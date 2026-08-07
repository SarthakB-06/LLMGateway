# Eval Service

> Production-quality LLM evaluation microservice — bias-mitigated judge, RAG metrics, CI regression gate.

Part of the [LLM Gateway](../README.md) monorepo. Runs on `:8001`.

## Quick Start

```bash
# From project root — infrastructure must be running first:
cd backend && docker compose up -d

# Start eval service locally
cd eval_service
uv venv && .venv\Scripts\activate
uv pip install -r requirements.txt
uvicorn src.main:app --port 8001 --reload
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/compare` | Fan-out prompt to multiple models |
| `POST` | `/api/v1/judge` | Bias-swapped LLM-as-judge |
| `POST` | `/api/v1/rag-eval` | RAG faithfulness + answer relevancy |
| `GET` | `/api/v1/history` | Eval history + bootstrap CI per model |
| `POST` | `/api/v1/recommend` | Best cost-quality model for a task type |
| `GET` | `/api/v1/pareto` | Pareto-optimal model frontier |

## Scripts

```bash
# Validate judge agreement vs human labels (requires service on :8001)
python scripts/validate_judge.py

# CI regression gate (exits 1 on regression)
$env:BENCHMARK_LIMIT="5"   # PowerShell
python scripts/run_benchmark.py
```

## Key Design Decisions

- **Double-call bias mitigation**: every judge call runs twice with A/B order swapped. Disagreement → `"inconclusive"`.
- **ragas 0.4.x schema**: `user_input`, `response`, `retrieved_contexts` (list). Uses `EvaluationDataset` + `SingleTurnSample`.
- **Bootstrap CI**: 1000-resample confidence intervals in pure stdlib (no NumPy).
- **ClickHouse migration**: `_init_table()` uses `ALTER TABLE ADD COLUMN IF NOT EXISTS` for every column — safe on both fresh and existing volumes.
