# 🚀 Enterprise AI Gateway & Eval Control Plane

> **Ultra-fast semantic caching · LLM-as-judge evaluation · Quality-gated smart routing · CI regression gate**

An enterprise-grade AI Gateway that dramatically reduces LLM cost and latency through vector-based semantic caching, and extends this with a production-quality evaluation layer: bias-mitigated LLM-as-judge scoring, RAG faithfulness metrics, bootstrap confidence intervals, and a feedback loop that routes live traffic to the best cost-quality model automatically.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-Vite-61DAFB?logo=react)](https://vitejs.dev)
[![Redis Stack](https://img.shields.io/badge/Redis-Stack-DC382D?logo=redis)](https://redis.io/docs/stack/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-MergeTree-FFCC01?logo=clickhouse)](https://clickhouse.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose/)

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT / FRONTEND                               │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTP
          ┌──────────────────▼──────────────────┐
          │          BACKEND GATEWAY             │   :8000
          │          (FastAPI + Uvicorn)         │
          │  /chat   /route   /analytics   /docs │
          └───┬───────────┬─────────────┬────────┘
              │           │             │
     ┌────────▼──┐  ┌─────▼────┐  ┌───▼──────────────┐
     │  Redis    │  │ClickHouse│  │  Gemini / Groq    │
     │  Stack    │  │(gateway  │  │  LLM Providers    │
     │ (semantic │  │  logs)   │  └───────────────────┘
     │  cache)   │  └──────────┘
     └───────────┘
              │  X-Internal-Key
     ┌────────▼──────────────────────┐
     │       EVAL SERVICE            │   :8001
     │      (FastAPI + Uvicorn)      │
     │ /compare  /judge  /rag-eval   │
     │ /recommend  /pareto  /history │
     └───────────┬───────────────────┘
                 │
          ┌──────▼──────┐
          │  ClickHouse │
          │ (eval_runs) │
          └─────────────┘
```

The system has **two independent FastAPI services** sharing a ClickHouse instance:

| Service | Port | Responsibility |
|---------|------|----------------|
| `backend/` | 8000 | Gateway: cache, routing, telemetry, provider proxy |
| `eval_service/` | 8001 | Eval: judge, RAG scoring, recommendations, CI gate |

Infrastructure (Redis Stack + ClickHouse) is managed by `backend/docker-compose.yml`.

---

## ✨ Feature Overview

### Gateway (`backend/`)
- **Semantic cache** — 3072-dim Gemini embeddings in Redis Stack, cosine similarity, ~5ms cache hits
- **Multi-provider routing** — Google Gemini (`gemini-2.5-flash`, `gemini-1.5-flash`) with Groq support ready
- **Quality-gated `/route`** — calls eval service for the best cost-quality model; 2s timeout with automatic fallback
- **Zero-block telemetry** — async ClickHouse writes (latency, tokens, cost, cache hit status)
- **React dashboard** — dark mode, real-time charts for cache rates, cost savings, model traffic

### Eval Service (`eval_service/`)
- **Bias-mitigated LLM-as-judge** — every comparison runs twice with A/B order swapped; disagreement → `"inconclusive"`
- **Per-dimension scoring** — correctness, completeness, clarity (1–5 each) + rationale
- **Bootstrap confidence intervals** — 1000-resample CI on composite scores (pure stdlib, no NumPy)
- **RAG evaluation** — faithfulness + answer relevancy via ragas 0.4.x + Gemini backend
- **Smart model recommendation** — picks cheapest model whose CI lower bound ≥ quality threshold
- **Pareto frontier** — flags models dominated on both cost and quality
- **CI regression gate** — `run_benchmark.py` exits non-zero if quality drops vs previous run
- **Human-judge validation** — `validate_judge.py` computes agreement % and Cohen's κ

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | Python 3.11, FastAPI, Uvicorn |
| **LLM Providers** | Google Gemini (`google-genai`), Groq |
| **Semantic Cache** | Redis Stack (RediSearch + Vector), `redisvl` |
| **Telemetry / Eval Storage** | ClickHouse MergeTree |
| **RAG Metrics** | `ragas` 0.4.x, `langchain-google-genai` |
| **Frontend Dashboard** | React, Vite, TypeScript, Tailwind CSS, Recharts |
| **Infrastructure** | Docker, Docker Compose |
| **Package Manager** | `uv` (recommended) or `pip` |

---

## 🚦 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- `uv` (recommended: `pip install uv`) or `pip`
- Node.js 18+ & npm
- A **Google Gemini API key** → [aistudio.google.com](https://aistudio.google.com)

---

### 1. Clone & Configure

```bash
git clone https://github.com/SarthakB-06/LLMGateway.git
cd llm-gateway
```

**Backend `.env`** — create `backend/.env`:
```env
GEMINI_API_KEY=your_google_gemini_api_key
INTERNAL_API_KEY=secret-internal-key-123
```

**Eval service `.env`** — create `eval_service/.env`:
```env
GEMINI_API_KEY=your_google_gemini_api_key
GATEWAY_URL=http://localhost:8000
INTERNAL_API_KEY=secret-internal-key-123
JUDGE_MODEL=gemini-2.5-flash
JUDGE_PROVIDER=google
```

---

### 2. Start Infrastructure (Redis + ClickHouse + eval_service)

```bash
cd backend
docker compose up -d
```

This starts:
- **Redis Stack** on `localhost:6379`
- **ClickHouse** on `localhost:8123`
- **eval_service** (Docker) on `localhost:8001`

---

### 3. Start the Backend Gateway

```bash
cd backend

# Using uv (recommended)
uv venv && .venv\Scripts\activate   # Windows
uv pip install -r requirements.txt
python -m src.main
```

Gateway is now at **http://localhost:8000** — Swagger UI at **http://localhost:8000/docs**

---

### 4. Start the Frontend Dashboard

```bash
cd frontend
npm install
npm run dev
```

Dashboard at **http://localhost:5173**

---

## 📡 API Reference

### Backend Gateway — `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/chat` | Standard LLM completion (with semantic cache) |
| `POST` | `/api/v1/route` | **Quality-gated smart routing** — picks best model via eval service |
| `GET` | `/api/v1/analytics/dashboard` | Cache hit rates, cost savings, model traffic |
| `POST` | `/internal/complete` | Internal endpoint for eval_service (requires `X-Internal-Key`) |

#### `POST /api/v1/route`
```json
{
  "prompt": "What is the capital of France?",
  "task_type": "factual",
  "min_quality_threshold": 3.5
}
```
Response:
```json
{
  "response": "Paris is the capital of France.",
  "model_used": "gemini-1.5-flash",
  "routing_source": "eval_recommendation",
  "latency_ms": 823,
  "tokens": 142,
  "cost": 0.0000213
}
```
`routing_source` values: `"cache"` | `"eval_recommendation"` | `"fallback"` | `"fallback_on_error"`

---

### Eval Service — `http://localhost:8001`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/compare` | Fan-out prompt to multiple models, return all responses |
| `POST` | `/api/v1/judge` | Bias-mitigated LLM-as-judge scoring |
| `POST` | `/api/v1/rag-eval` | RAG faithfulness + answer relevancy via ragas |
| `GET` | `/api/v1/history` | Eval run history with bootstrap CI model summary |
| `POST` | `/api/v1/recommend` | Best cost-quality model recommendation |
| `GET` | `/api/v1/pareto` | Pareto-optimal model frontier |

#### `POST /api/v1/judge`
```json
{
  "prompt": "What is the capital of Australia?",
  "responses": {
    "gemini-2.5-flash": "Canberra is the capital of Australia.",
    "gemini-1.5-flash": "The capital of Australia is Sydney."
  },
  "task_type": "factual"
}
```
Response:
```json
{
  "run_id": "...",
  "evaluation": {
    "response_a": { "correctness": 5, "completeness": 4, "clarity": 5, "rationale": "..." },
    "response_b": { "correctness": 1, "completeness": 2, "clarity": 3, "rationale": "..." },
    "verdict": "A",
    "judge_verdict": "A",
    "_judge_metrics": { "latency_ms": 2840, "cost": 0.00004, "run1_verdict": "A", "run2_verdict_normalised": "A" }
  }
}
```

> **`judge_verdict`** is the bias-corrected field. When the two calls disagree (position bias detected), it returns `"inconclusive"` instead of a potentially wrong winner.

#### `POST /api/v1/rag-eval`
```json
{
  "question": "What caching mechanism does the gateway use?",
  "context": "The LLM Gateway uses a Redis Stack semantic cache. Cache hits are served in ~5ms.",
  "answer": "The gateway uses Redis Stack with cosine similarity for semantic caching.",
  "model": "gemini-2.5-flash"
}
```
Response:
```json
{
  "scores": {
    "faithfulness_score": 0.94,
    "groundedness_score": 0.88,
    "error": null
  }
}
```

#### `POST /api/v1/recommend`
```json
{ "task_type": "factual", "min_quality_threshold": 3.5 }
```
Response:
```json
{
  "recommended_model": "gemini-1.5-flash",
  "expected_cost": 0.00000015,
  "expected_quality_lower_bound": 3.8,
  "confidence_interval": { "mean": 4.1, "lower": 3.8, "upper": 4.4, "n": 12 }
}
```

#### `GET /api/v1/pareto`
Returns all evaluated models with `is_pareto_optimal` flag. A model is Pareto-dominated if another model has both strictly higher quality CI lower bound AND strictly lower average cost.

---

## 🧪 Benchmarking & CI

### Golden Dataset
`eval_service/benchmarks/golden_dataset.json` — 50 prompts across 5 categories:
- **factual** (TruthfulQA-inspired) — tests hallucination resistance
- **reasoning** — logic and computation
- **coding** — Python / SQL / algorithms
- **safety** — refusal behaviour
- **rag** — gateway-specific knowledge

### Human-Judge Validation

```bash
# Requires eval_service running on :8001
python eval_service/scripts/validate_judge.py
```

Computes agreement % and Cohen's κ across 15 hand-labelled examples. Target: κ ≥ 0.6.

### Regression Benchmark

```bash
# PowerShell
$env:EVAL_SERVICE_URL = "http://localhost:8001"
$env:BENCHMARK_LIMIT  = "20"
python eval_service/scripts/run_benchmark.py
```

- Runs fan-out compare + judge on each dataset entry
- Computes bootstrap CI for composite scores
- Compares CI lower bound vs previous run in ClickHouse
- **Exits 1** if quality drops > `REGRESSION_THRESHOLD` (default 0.3 points)

### GitHub Actions

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `eval-gate.yml` | PR touching `eval_service/src/` or `backend/src/` | Blocks merge on quality regression |
| `nightly-eval.yml` | Daily 00:00 UTC | Posts Discord/Slack webhook alert on regression |

Add `GEMINI_API_KEY` and (optionally) `EVAL_WEBHOOK_URL` to GitHub Secrets.

---

## 📁 Project Structure

```
llm-gateway/
├── backend/                    # Gateway service
│   ├── docker-compose.yml      # Redis + ClickHouse + eval_service
│   ├── src/
│   │   ├── api/v1/
│   │   │   ├── chat.py         # /chat endpoint
│   │   │   ├── route.py        # /route quality-gated endpoint
│   │   │   ├── analytics.py    # /analytics/dashboard
│   │   │   └── internal.py     # /internal/complete (eval_service bridge)
│   │   ├── services/
│   │   │   ├── cache.py        # Redis semantic cache
│   │   │   └── telemetry.py    # ClickHouse async telemetry
│   │   └── core/config.py
│   └── requirements.txt
│
├── eval_service/               # Evaluation & trust service
│   ├── src/
│   │   ├── api/v1/router.py    # All eval endpoints
│   │   ├── services/
│   │   │   ├── judge.py        # Bias-swapped LLM-as-judge
│   │   │   ├── faithfulness.py # ragas 0.4.x RAG metrics
│   │   │   ├── stats.py        # Bootstrap CI (pure stdlib)
│   │   │   └── clickhouse_writer.py  # eval_runs schema + migration
│   │   └── models/schemas.py
│   ├── benchmarks/
│   │   ├── golden_dataset.json # 50-entry evaluation dataset
│   │   ├── rag_benchmark.json  # 15 RAG-specific entries
│   │   └── human_labels.json   # 15 hand-labelled A/B pairs for κ
│   └── scripts/
│       ├── run_benchmark.py    # CI regression gate
│       └── validate_judge.py   # Human-judge agreement
│
├── frontend/                   # React observability dashboard
│   └── src/
│
└── .github/workflows/
    ├── eval-gate.yml           # PR quality gate
    └── nightly-eval.yml        # Nightly monitoring
```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Google Gemini API key |
| `INTERNAL_API_KEY` | `secret-internal-key-123` | Shared secret for eval_service bridge |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis Stack connection |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse host |
| `CLICKHOUSE_PASSWORD` | `gateway_secure_123` | ClickHouse password |
| `EVAL_SERVICE_URL` | `http://localhost:8001` | Eval service base URL (for /route) |

### Eval Service (`eval_service/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Used by ragas and judge model |
| `GATEWAY_URL` | `http://localhost:8000` | Backend gateway URL |
| `INTERNAL_API_KEY` | `secret-internal-key-123` | Must match backend |
| `JUDGE_MODEL` | `gemini-2.5-flash` | Model used for LLM-as-judge |
| `JUDGE_PROVIDER` | `google` | Provider for judge model |
| `CLICKHOUSE_HOST` | `localhost` | Same ClickHouse instance as backend |
| `CLICKHOUSE_PASSWORD` | `gateway_secure_123` | ClickHouse password |

---

## 🔬 How the Eval Pipeline Works

```
User prompt
    │
    ├── POST /compare ──────► Gateway (fan-out) ──► Model A response
    │                                            └► Model B response
    │
    └── POST /judge ─────────────────────────────────────────────┐
              │                                                   │
              ├── Call 1: Judge scores A vs B (A-first order)     │
              └── Call 2: Judge scores B vs A (swapped order)     │
                         │                                        │
                         ├── Both agree → judge_verdict = winner  │
                         └── Disagree  → judge_verdict = "inconclusive"
                                    │
                    Scores saved to ClickHouse (eval_runs)
                                    │
                    POST /recommend: bootstrap CI per model
                                    │
                    Return cheapest model with CI lower ≥ threshold
                                    │
                    POST /route (backend): use recommendation
```

---

## 📊 ClickHouse Tables

### `gateway_logs` (backend telemetry)
| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | DateTime | Request time |
| `model` | String | Model used |
| `latency_ms` | Float32 | End-to-end latency |
| `cache_hit` | UInt8 | 1 = cache hit |
| `cache_type` | String | `"semantic"` or `""` |
| `total_tokens` | UInt32 | Tokens consumed |
| `estimated_cost` | Float64 | USD cost |

### `eval_runs` (eval service)
| Column | Type | Description |
|--------|------|-------------|
| `run_id` | UUID | Evaluation run ID |
| `model` | String | Model evaluated |
| `correctness_score` | Nullable(UInt8) | Judge score 1–5 |
| `completeness_score` | Nullable(UInt8) | Judge score 1–5 |
| `clarity_score` | Nullable(UInt8) | Judge score 1–5 |
| `judge_verdict` | Nullable(String) | Bias-corrected verdict |
| `task_type` | Nullable(String) | e.g. `"factual"`, `"coding"` |
| `faithfulness_score` | Nullable(Float64) | ragas faithfulness |
| `rag_groundedness_score` | Nullable(Float64) | ragas answer relevancy |
| `prompt_version` | Nullable(String) | Git commit hash |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. PRs touching `eval_service/src/` or `backend/src/` automatically trigger the eval quality gate
4. Ensure `python eval_service/scripts/run_benchmark.py` exits 0 before submitting

---

*Architected and engineered by Sarthak Bansal.*
