**English** | [中文](README.md)

<div align="center">

# MultiAgentIR

**Heterogeneous Model Collaborative Deep Research System**

A multi-agent intelligent retrieval and analysis framework built on FastAPI + LangGraph, featuring heterogeneous model routing, agent role decomposition, and switchable topology orchestration to automatically generate high-quality deep research reports.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C.svg)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## System Architecture

<div align="center">
  <img src="fig/fig1.png" alt="System Architecture" width="800"/>
</div>

---

## Key Highlights

- **Heterogeneous Model Collaboration** — Agents automatically route to different models based on capability requirements; low-cost models for volume, powerful models for quality control
- **Dual Topology Orchestration** — Hierarchical topology for industry reports, Debate topology for open-ended questions, with pluggable extensibility
- **Configuration-Driven** — Add models, agents, prompts, and topologies via YAML without modifying core code
- **Engineering Observability** — Full-chain logging of model calls, costs, latency, tokens, and audit trails
- **Security Extensions** — Built-in interfaces for Prompt Injection detection, PII desensitization, audit tracing, and citation verification

---

## Topology Orchestration

### Topology A: Hierarchical (Industry Reports)

Suitable for structured, fact-dependent research tasks (industry analysis, competitive research, technology trends):

```
        Planner
           ↓
     SubQuestion List
           ↓
 ┌─────────┼─────────┐
 ↓         ↓         ↓
Searcher  Searcher  Searcher
 ↓         ↓         ↓
Reader    Reader    Reader
 └─────────┼─────────┘
           ↓
        Analyzer
           ↓
        Critic
           ↓
        Writer
           ↓
      Final Report
```

### Topology B: Debate (Open-Ended Questions)

Suitable for controversial analysis, strategy selection, and non-standard-answer questions:

```
          Planner
             ↓
       Debate Questions
             ↓
 ┌───────────┼───────────┐
 ↓           ↓           ↓
Pro Agent   Con Agent   Neutral Agent
 ↓           ↓           ↓
Evidence    Evidence    Evidence
 └───────────┼───────────┘
             ↓
          Critic
             ↓
        Synthesizer
             ↓
          Writer
             ↓
      Final Research Memo
```

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Primary language |
| FastAPI | API service & OpenAPI docs |
| LangGraph + asyncio | Agent workflow orchestration & parallel execution |
| Pydantic v2 | Schema validation & data modeling |
| Redis | Caching, task state persistence, rate limiting |
| tenacity | Retry, backoff, circuit breaker recovery |
| httpx | Async HTTP client |
| Vue 3 + TailwindCSS | Frontend UI |

---

## Agent Roles

| Agent | Responsibility | Model Requirement |
|-------|---------------|-------------------|
| **Planner** | Task understanding & decomposition | Strong reasoning |
| **Searcher** | Query rewriting & web retrieval | Web search capability |
| **Reader** | Long-text reading & summary extraction | Cost-effective long context |
| **Analyzer** | Cross-source analysis & contradiction detection | Long context analysis |
| **Critic** | Critical review & fact-checking | Strong reasoning |
| **Writer** | Structured research report generation | Strong writing |
| **Validator** | Output schema validation & quality assurance | Lightweight validation |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (optional; falls back to in-memory cache if unavailable)

### 1. Start the Backend

```bash
cd deep_research_system

# Create virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and fill in at least one model API key

# Start the server
python main.py
```

### 2. Start the Frontend

```bash
cd deep_research_system/frontend

npm install
npm run dev
```

Visit `http://localhost:3000` to use the application.

### 3. Quick Verification

```bash
# Health check
curl http://localhost:8000/api/health

# Submit a research task
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "AI Agent market trend analysis 2025", "task_type": "industry_report", "depth": "quick"}'
```

---

## Project Structure

```
deep_research_system/
├── main.py                  # Backend entry point
├── .env                     # Environment variables
├── config/                  # YAML configs (models, agents, topology)
├── prompts/                 # Jinja2 prompt templates (versioned)
│   ├── planner/             # Planner agent prompts
│   ├── searcher/            # Searcher agent prompts
│   ├── reader/              # Reader agent prompts
│   ├── analyzer/            # Analyzer agent prompts
│   ├── critic/              # Critic agent prompts
│   ├── writer/              # Writer agent prompts
│   ├── validator/           # Validator agent prompts
│   └── debate/              # Debate agent prompts
├── app/
│   ├── agents/              # Agent implementations (Planner/Searcher/Reader/...)
│   ├── topology/            # Topology orchestration (Hierarchical / Debate)
│   ├── model_pool/          # Model routing, key pool, circuit breaker
│   ├── schemas/             # Pydantic data models
│   ├── services/            # Business services (search/cache/task state)
│   └── core/                # Config/logging/middleware/security
├── frontend/                # Vue 3 frontend
├── tests/                   # Test cases
└── output/reports/          # Generated reports
```

---

## Model Configuration

The system supports heterogeneous model integration via `config/models.yaml`. Three model categories are recommended for the initial setup:

| Model Type | Recommended For | Example |
|------------|----------------|---------|
| Web-search model | Searcher | DeepSeek-Chat |
| Cost-effective long-context model | Reader / Analyzer | GLM-4-Long |
| Strong reasoning/writing model | Planner / Critic / Writer | DeepSeek-Reasoner |

All models are accessed via API, compatible with the OpenAI interface standard, and support Chinese model providers.

---

## License

MIT
