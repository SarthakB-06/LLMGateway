#!/usr/bin/env python3

import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parents[1]))

EVAL_SERVICE_URL = os.getenv("EVAL_SERVICE_URL", "http://localhost:8001")
LABELS_PATH = Path(__file__).parents[1] / "benchmarks" / "human_labels.json"


async def call_judge(prompt: str, response_a: str, response_b: str, model_a: str = "ModelA", model_b: str = "ModelB") -> dict:
    """Call eval_service /judge endpoint and return the evaluation."""
    import httpx
    payload = {
        "prompt": prompt,
        "responses": {model_a: response_a, model_b: response_b},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{EVAL_SERVICE_URL}/api/v1/judge", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Map model_a/model_b back to A/B labels
        judge_verdict = data.get("evaluation", {}).get("judge_verdict", "tie")
        # /judge response maps model names; translate back to A/B
        return judge_verdict


def cohen_kappa(labels_human: list, labels_judge: list, categories: list) -> float:
    """
    Compute Cohen's kappa for two annotators.
    Pure stdlib — no scipy required.
    
    κ = (P_o - P_e) / (1 - P_e)
    where P_o = observed agreement, P_e = expected agreement by chance.
    """
    n = len(labels_human)
    assert n == len(labels_judge), "Label lists must be the same length"
    assert n > 0, "Need at least one label"

    # Observed agreement
    p_o = sum(1 for h, j in zip(labels_human, labels_judge) if h == j) / n

    # Expected agreement
    p_e = 0.0
    for cat in categories:
        p_human = labels_human.count(cat) / n
        p_judge = labels_judge.count(cat) / n
        p_e += p_human * p_judge

    if p_e == 1.0:
        return 1.0  # Perfect agreement even in edge case

    kappa = (p_o - p_e) / (1 - p_e)
    return kappa


def map_verdict_to_ab(verdict: str, model_a_key: str, model_b_key: str) -> str:
    """Normalise verdict to 'A' | 'B' | 'tie' | 'inconclusive'."""
    if verdict == model_a_key:
        return "A"
    if verdict == model_b_key:
        return "B"
    return verdict  # 'tie', 'inconclusive' pass through


async def main():
    if not LABELS_PATH.exists():
        print(f"ERROR: human_labels.json not found at {LABELS_PATH}")
        sys.exit(1)

    with open(LABELS_PATH) as f:
        labels = json.load(f)

    print(f"\nValidating judge on {len(labels)} hand-labelled examples...")
    print(f"Eval service: {EVAL_SERVICE_URL}\n")
    print(f"{'ID':<15} {'Human':>12} {'Judge':>12} {'Match':>6}")
    print("-" * 50)

    human_verdicts = []
    judge_verdicts = []
    errors = 0

    for item in labels:
        try:
            judge_v = await call_judge(
                prompt=item["prompt"],
                response_a=item["response_a"],
                response_b=item["response_b"],
            )

            human_v = item["human_verdict"]
            match = "✓" if judge_v == human_v else "✗"

            print(f"{item['id']:<15} {human_v:>12} {judge_v:>12} {match:>6}")

            human_verdicts.append(human_v)
            judge_verdicts.append(judge_v)

        except Exception as e:
            print(f"{item['id']:<15} {'ERROR':>12} {str(e)[:20]:>12} {'?':>6}")
            errors += 1

    if not human_verdicts:
        print("\nNo results — all calls failed.")
        sys.exit(1)

    print("-" * 50)

    # Agreement (exclude inconclusive from denominator for cleaner metric)
    total = len(human_verdicts)
    matching = sum(1 for h, j in zip(human_verdicts, judge_verdicts) if h == j)
    agreement_pct = (matching / total) * 100

    # Cohen's kappa
    categories = list(set(human_verdicts + judge_verdicts))
    kappa = cohen_kappa(human_verdicts, judge_verdicts, categories)

    print(f"\nResults ({total} examples, {errors} errors):")
    print(f"  Agreement:    {agreement_pct:.1f}%")
    print(f"  Cohen's κ:    {kappa:.3f}")
    print()
    print("README line:")
    print(f'  "Judge agreement with human labels: {agreement_pct:.0f}% (Cohen\'s κ = {kappa:.2f}, n={total})"')
    print()

    if kappa < 0.4:
        print("⚠  κ < 0.4: Fair agreement — judge reliability is questionable. Consider refining the rubric.")
    elif kappa < 0.6:
        print("✓  κ in [0.4, 0.6]: Moderate agreement — acceptable for automated evaluation.")
    else:
        print("✓✓ κ ≥ 0.6: Substantial agreement — judge is reliable.")


if __name__ == "__main__":
    asyncio.run(main())

