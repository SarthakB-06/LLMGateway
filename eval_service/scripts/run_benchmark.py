#!/usr/bin/env python3
"""
run_benchmark.py — CI/CD regression gate for eval quality.

Usage:
    python eval_service/scripts/run_benchmark.py

Environment variables:
    EVAL_SERVICE_URL     Base URL of the eval service (default: http://localhost:8001)
    BENCHMARK_MODELS     Comma-separated provider:model pairs
                         (default: google:gemini-2.5-flash,google:gemini-2.0-flash)
    REGRESSION_THRESHOLD Max allowed drop in CI lower-bound vs previous run (default: 0.3)
    BENCHMARK_LIMIT      How many dataset entries to run (default: 20, for speed in CI)
    CLICKHOUSE_HOST      ClickHouse host for reading previous run (default: localhost)
    CLICKHOUSE_PASSWORD  ClickHouse password (default: gateway_secure_123)
    PROMPT_VERSION       Override git commit hash (optional)

Exit codes:
    0 — All checks pass (no regression)
    1 — Quality regression detected or fatal error
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx


EVAL_SERVICE_URL    = os.getenv("EVAL_SERVICE_URL", "http://localhost:8001")
REGRESSION_THRESHOLD = float(os.getenv("REGRESSION_THRESHOLD", "0.3"))
BENCHMARK_LIMIT     = int(os.getenv("BENCHMARK_LIMIT", "20"))
CLICKHOUSE_HOST     = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "gateway_secure_123")

DEFAULT_MODELS = [
    {"provider": "google", "model": "gemini-2.5-flash"},
    {"provider": "google", "model": "gemini-2.0-flash"},
]

def parse_models() -> list:
    raw = os.getenv("BENCHMARK_MODELS", "")
    if not raw:
        return DEFAULT_MODELS
    result = []
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            provider, model = entry.split(":", 1)
            result.append({"provider": provider, "model": model})
    return result or DEFAULT_MODELS


def get_prompt_version() -> str:
    override = os.getenv("PROMPT_VERSION", "")
    if override:
        return override
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


DATASET_PATH = Path(__file__).parents[1] / "benchmarks" / "golden_dataset.json"


async def call_compare(prompt: str, models: list, client: httpx.AsyncClient) -> dict:
    resp = await client.post(
        f"{EVAL_SERVICE_URL}/api/v1/compare",
        json={"prompt": prompt, "models": models},
        timeout=90.0,
    )
    resp.raise_for_status()
    return resp.json()


async def call_judge(prompt: str, responses: dict, task_type: str, prompt_version: str, client: httpx.AsyncClient) -> dict:
    resp = await client.post(
        f"{EVAL_SERVICE_URL}/api/v1/judge",
        json={
            "prompt": prompt,
            "responses": responses,
            "task_type": task_type,
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()



def get_previous_lower_bound(current_version: str) -> float | None:
    """
    Query ClickHouse for the CI lower bound of the most recent run
    with a different prompt_version than the current one.
    Returns None if no previous data exists.
    """
    try:
        import clickhouse_connect
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            password=CLICKHOUSE_PASSWORD,
            username="default",
        )
        query = f"""
        SELECT
            avg((correctness_score + completeness_score + clarity_score) / 3.0) as avg_score,
            prompt_version
        FROM eval_runs
        WHERE correctness_score IS NOT NULL
          AND prompt_version IS NOT NULL
          AND prompt_version != '{current_version}'
        GROUP BY prompt_version
        ORDER BY max(timestamp) DESC
        LIMIT 1
        """
        result = client.query(query)
        if result.result_rows:
            # Return the avg as a rough lower-bound proxy for previous runs
            # (we can't re-bootstrap, but avg is a conservative approximation)
            return float(result.result_rows[0][0])
    except Exception as e:
        print(f"[ClickHouse] Could not fetch previous run data: {e}")
    return None



def bootstrap_ci(values: list, n_resamples: int = 1000, lower_pct: float = 5.0) -> dict:
    import random, statistics
    if not values:
        return {"mean": 0.0, "lower": 0.0, "upper": 0.0, "n": 0}
    n = len(values)
    mean = statistics.mean(values)
    if n == 1:
        return {"mean": mean, "lower": mean, "upper": mean, "n": n}
    boot_means = sorted(statistics.mean(random.choices(values, k=n)) for _ in range(n_resamples))
    lower_idx = max(0, int((lower_pct / 100.0) * n_resamples) - 1)
    upper_idx = min(n_resamples - 1, int(((100 - lower_pct) / 100.0) * n_resamples) - 1)
    return {"mean": round(mean, 4), "lower": round(boot_means[lower_idx], 4), "upper": round(boot_means[upper_idx], 4), "n": n}



async def main():
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    models = parse_models()
    prompt_version = get_prompt_version()

    subset = dataset[:BENCHMARK_LIMIT]
    print(f"Running benchmark: {len(subset)} examples | models: {[m['model'] for m in models]} | version: {prompt_version}")
    print(f"Eval service: {EVAL_SERVICE_URL}\n")

    composite_scores = []
    errors = 0

    async with httpx.AsyncClient() as http:
        for i, entry in enumerate(subset):
            prompt = entry["prompt"]
            category = entry.get("category", "general")
            print(f"  [{i+1:02d}/{len(subset):02d}] {entry['id']}: ", end="", flush=True)

            try:
                # Step 1: fan-out compare
                compare_result = await call_compare(prompt, models, http)
                results = compare_result.get("results", [])

                # Build responses dict: only include non-error results
                responses = {
                    r["model"]: r["response"]
                    for r in results
                    if "response" in r and "error" not in r
                }

                if len(responses) < 2:
                    print("SKIP (not enough model responses)")
                    errors += 1
                    continue

                # Use only first two models for judge
                model_names = list(responses.keys())[:2]
                responses_pair = {k: responses[k] for k in model_names}

                # Step 2: judge
                judge_result = await call_judge(prompt, responses_pair, category, prompt_version, http)
                evaluation = judge_result.get("evaluation", {})

                # Collect composite scores for each model
                for key in ["response_a", "response_b"]:
                    scores = evaluation.get(key, {})
                    c, co, cl = scores.get("correctness"), scores.get("completeness"), scores.get("clarity")
                    vals = [v for v in [c, co, cl] if v is not None]
                    if vals:
                        import statistics
                        composite_scores.append(statistics.mean(vals))

                verdict = evaluation.get("judge_verdict", "?")
                print(f"verdict={verdict}")

            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

    print(f"\nCompleted: {len(subset) - errors}/{len(subset)} examples succeeded")

    if not composite_scores:
        print("ERROR: No scores collected — cannot evaluate quality.")
        sys.exit(1)

    # Compute CI for current run
    current_ci = bootstrap_ci(composite_scores)
    print(f"\nCurrent run quality CI:")
    print(f"  Mean:  {current_ci['mean']:.4f}")
    print(f"  Lower: {current_ci['lower']:.4f}  (5th percentile, 1000 resamples)")
    print(f"  Upper: {current_ci['upper']:.4f}  (95th percentile)")
    print(f"  N:     {current_ci['n']} score observations")

    # Check for regression
    prev_lower = get_previous_lower_bound(prompt_version)
    if prev_lower is not None:
        print(f"\nPrevious run lower bound (approx): {prev_lower:.4f}")
        drop = prev_lower - current_ci["lower"]
        print(f"Drop vs previous: {drop:.4f} (threshold: {REGRESSION_THRESHOLD})")
        if drop > REGRESSION_THRESHOLD:
            print(f"\n REGRESSION DETECTED: quality dropped {drop:.3f} points below previous run.")
            print(f"   Current lower bound: {current_ci['lower']:.4f}")
            print(f"   Previous lower bound: {prev_lower:.4f}")
            print(f"   Threshold: {REGRESSION_THRESHOLD}")
            sys.exit(1)
        else:
            print(f"\n No regression detected (drop {drop:.3f} < threshold {REGRESSION_THRESHOLD}).")
    else:
        print("\n[INFO] No previous run found in ClickHouse — skipping regression check for this run.")
        print("       This run's scores will serve as the baseline for future comparisons.")

    print(f"\n Benchmark passed — version {prompt_version}")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

