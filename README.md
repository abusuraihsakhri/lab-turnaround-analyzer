# Lab Turnaround Analyzer

> **Domain:** Computational Biology & Clinical Laboratory Informatics
> **Standards:** wwPDB, IUPAC, CLSI, CAP, NIST

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

---

## 📖 What It Does

Lab Turnaround Time Analyzer processes laboratory LIS timestamps to calculate:
- TAT (Turnaround Time) percentiles
- Breach rate analysis
- Outlier detection and alerting
- Reference range validation
- Quality control monitoring

Features a multi-worker agent architecture with HMAC-SHA256 tamper-evident audit trails and zero-PHI outbound data protection.

---

## ⚙️ Key Components

### Core Modules

| Module | Purpose |
|--------|---------|
| `tat_analyzer.py` | Core lookup engine and CSV processor |
| `cli.py` | Command-line interface for all operations |
| `simulator.py` | High-throughput simulation and stress testing |
| `enrichment.py` | Domain-specific analytical feature engines |

### Agent System (`agents/`)

| Module | Purpose |
|--------|---------|
| `base.py` | PHI guard, HMAC-SHA256 audit trail, security exceptions |
| `models.py` | Pydantic data models for tasks, alerts, and dossiers |
| `supervisor.py` | Multi-worker orchestration and consensus |
| `workers.py` | Specialized QC, safety, and conformance workers |
| `api.py` | FastAPI REST endpoints |
| `llm_factory.py` | LLM provider abstraction (mock, Ollama, Claude, OpenAI) |
| `learning.py` | Bayesian calibration and active learning |
| `metrics.py` | Prometheus metrics exporter |
| `streamer.py` | WebSocket telemetry broadcasting |

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/lab-turnaround-analyzer.git
cd lab-turnaround-analyzer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

---

## 🚀 Usage

### CLI Commands

```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch process CSV records
python cli.py batch -i input.csv -o results.csv

# Chat with supervisor
python cli.py chat "Explain current system status"

# Verify audit trail integrity
python cli.py verify-audit

# Launch FastAPI server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Direct Analyzer Usage

```bash
# Single lookup
python tat_analyzer.py single creatinine

# Batch CSV processing
python tat_analyzer.py batch --input sample.csv --output results.csv
```

### Run Simulation

```bash
# Default 100 iterations
python simulator.py

# Custom iteration count
python simulator.py 1000
```

---

## 🧪 Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=agents --cov=tat_analyzer
```

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or manually
docker build -t lab-turnaround-analyzer .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key lab-turnaround-analyzer
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 signing key for audit trail | Random per-session |
| `MODEL_PROVIDER` | LLM provider (mock/ollama/claude/openai) | mock |

See `.env.example` for full configuration options.

---

## 🛡️ Security Features

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail:** Cryptographically chained, tamper-evident logging
- **Path Traversal Protection:** Input/output file path validation
- **No Hardcoded Secrets:** All secrets via environment variables

---

## 📁 Project Structure

```
lab-turnaround-analyzer/
├── agents/                 # Multi-agent system
│   ├── api.py             # FastAPI REST server
│   ├── base.py            # Security, PHI guard, audit trail
│   ├── models.py          # Pydantic data models
│   ├── supervisor.py      # Orchestration and consensus
│   ├── workers.py         # Specialized worker agents
│   ├── llm_factory.py     # LLM provider abstraction
│   ├── learning.py        # Bayesian calibration
│   ├── metrics.py         # Prometheus metrics
│   └── streamer.py        # WebSocket telemetry
├── tests/                 # Test suite
├── web/                   # Web console (HTML)
├── cli.py                 # CLI entry point
├── tat_analyzer.py        # Core analyzer
├── simulator.py           # Simulation runner
├── enrichment.py          # Feature engines
├── pyproject.toml         # Project configuration
├── Dockerfile             # Container build
├── docker-compose.yml     # Container orchestration
└── openapi_spec.json      # OpenAPI specification
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
