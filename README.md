# 🚀 Enterprise AI Gateway & Observability Control Plane

An ultra-fast, asynchronous AI Gateway engineered to dramatically reduce LLM API costs and latency. By implementing a vector-based Semantic Cache and zero-block telemetry, this microservice architecture intercepts redundant requests, routes dynamically across multiple providers (Google & Groq), and visualizes system performance in real-time.

![Gateway Dashboard](https://img.shields.io/badge/Architecture-Microservices-blue)
![Python](https://img.shields.io/badge/Python-FastAPI-009688)
![React](https://img.shields.io/badge/React-Vite-61DAFB)
![Databases](https://img.shields.io/badge/Redis_Stack_%7C_ClickHouse-Data-red)

## 🏗️ System Architecture

This platform is divided into four strictly decoupled layers:

### 1. The Data Plane (FastAPI)
A high-throughput, asynchronous routing engine. It acts as a universal proxy, dynamically multiplexing incoming traffic between Google Gemini (e.g., `gemini-2.5-flash`) and Groq's LPU hardware (e.g., `llama3-8b-8192`, `mixtral-8x7b-32768`) based on the requested model.

### 2. The Memory Layer (Redis Stack Vector Database)
A self-healing semantic cache. Instead of relying on exact string matching, incoming prompts are converted into 3072-dimensional embeddings. Redis performs mathematical cosine similarity searches in sub-milliseconds. If a user asks *"How do I make a Margarita?"* and another asks *"What are the ingredients of a Margarita?"*, the Gateway recognizes the semantic match and serves the cached response—bypassing the external API completely, dropping latency to ~5ms, and reducing API cost to $0.00.

### 3. The Telemetry Pipeline (ClickHouse)
A zero-block background worker. Upon request completion, usage metrics (tokens processed, estimated cost, latency, cache hit status) are asynchronously streamed into ClickHouse via a high-performance `MergeTree` table, ensuring the user experiences zero delay while analytics are aggregated.

### 4. The Control Plane (React + Vite + Recharts)
A dark-mode, enterprise-grade observability dashboard. It polls aggregated ClickHouse data via a secure Python API endpoint, rendering real-time visualizations of semantic cache hit rates, model traffic distribution, and financial API savings.

---

## ✨ Core Features

* **Vector Semantic Caching:** Achieves 85%+ cache hit rates on repeated conceptual queries using Google's `gemini-embedding-001` model.
* **Multi-Provider Routing:** Seamlessly switches between Google GenAI and Groq APIs on the fly.
* **Self-Calibrating Dimensions:** The Redis indexing engine automatically detects and calibrates to dynamic vector dimensions upon initialization.
* **Real-Time Observability:** Tracks total tokens processed, average latency drops, and calculates exact fractions of a cent saved per request.

---

## 🛠️ Tech Stack

**Backend Engine:** Python, FastAPI, Uvicorn, Google GenAI SDK, Groq SDK
**Databases:** Redis Stack (Hash Storage + RediSearch), ClickHouse (MergeTree Engine)
**Frontend Dashboard:** React, Vite, TypeScript, Tailwind CSS, Recharts, Lucide Icons
**Infrastructure:** Docker, Docker Compose, `uv` (Ultra-fast Python package manager)

---

## 🚦 Quick Start Guide

### Prerequisites
* Docker & Docker Compose
* `uv` (or `pip`)
* Node.js & npm

### 1. Spin up the Infrastructure
Start the Redis Vector Database and ClickHouse Analytics node:
```bash
cd backend
docker compose up -d

### 2. Configure Environment Variables
Create a `.env` file in the `/backend` directory:
```env
GEMINI_API_KEY="your_google_api_key"
GROQ_API_KEY="your_groq_api_key"

### 3. Start the Backend API
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python -m src.main

The FastAPI Swagger UI is now available at http://localhost:8000/docs

### 4. Start the Control Plane
Open a new terminal and boot the React dashboard:
```bash
cd frontend
npm install
npm run dev

Architected and engineered by Sarthak Bansal.
