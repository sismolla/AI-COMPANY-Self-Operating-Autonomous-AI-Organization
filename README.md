<div align="center">

# 🤖 AI-COMPANY

### *A Self-Operating, Multi-Agent AI Organization*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![LLM: Multi-Provider](https://img.shields.io/badge/LLM-Multi--Provider-blueviolet?style=for-the-badge)](https://openai.com/)
[![Offline Mode](https://img.shields.io/badge/Offline%20Mode-Supported-green?style=for-the-badge)](#-supported-llm-providers)

**AI-COMPANY** is a fully autonomous, self-hosted multi-agent AI organization. It runs like a real company — with a CEO director, specialized AI employees, persistent memory, a self-building tool factory, and a real-time web control center. You set the objectives; the AI handles everything else.

[**Quick Start**](#-quickstart) · [**Architecture**](#-architecture) · [**Agents**](#-the-autonomous-ai-workforce) · [**Tool Factory**](#-the-self-building-tool-factory) · [**Docker Deploy**](#2-run-with-docker-compose-production) · [**Configuration**](#%EF%B8%8F-configuration)

</div>

---

## ✨ Why AI-COMPANY?

Most AI tools give you a single assistant. **AI-COMPANY gives you an entire organization.**

| Feature | Description |
|---|---|
| 🧠 **Multi-Agent Hierarchy** | CEO director + 6 specialized autonomous agents with individual memories and workspaces |
| 🏭 **Self-Building Tool Factory** | Agents synthesize, sandbox-test, and deploy their own Python tools on demand |
| 🛡️ **4-Level Permission Matrix** | Least-privilege security from read-only research up to human-approved critical actions |
| 🔌 **Multi-LLM Support** | OpenAI, Gemini, Anthropic Claude, Ollama local models, or built-in offline mock |
| 📊 **Real-Time Web Dashboard** | FastAPI-powered dark-mode control center with live metrics and task management |
| 💾 **Persistent Memory** | Episodic + long-term memory per agent, persisted across sessions in SQLite/PostgreSQL |
| 📡 **Social Platform Integration** | Publish to Telegram, LinkedIn, and Facebook (with Director approval) |
| 🐳 **Docker-First Deployment** | One-command production stack with PostgreSQL + Redis |
| 🧪 **Full Test Suite** | Unit and end-to-end integration tests with `pytest` |

---

## 🏛️ Architecture

```
                           ┌──────────────┐
                           │  HUMAN OWNER │
                           │   (You/API)  │
                           └──────┬───────┘
                                  │ Sets Objectives & Approves Level 4
                                  ▼
                           ┌──────────────┐
                           │   AI CEO     │
                           │  (Director)  │
                           └──────┬───────┘
                                  │ Plans · Supervises · Delegates
      ┌──────────┬────────────────┼──────────────┬──────────────┐
      ▼          ▼                ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Engineering│ │ Research │ │Marketing │ │Analytics │ │Operations│
│  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
                                                    ┌──────────┐
                                                    │ Quality  │
                                                    │& Security│
                                                    └──────────┘
                        ═══════════════════════════════
                                SHARED INFRASTRUCTURE
                   • SQLite / PostgreSQL   • AST Sandboxed Tool Runner
                   • Persistent Task Queue • Autonomous Scheduler Loop
                   • Universal LLM Adapter • FastAPI Real-Time Dashboard
                   • Persistent Memory     • Redis Task Queue (optional)
```

---

## 👥 The Autonomous AI Workforce

| Agent | Role | Capabilities | Clearance |
|:---|:---|:---|:---:|
| **🎯 AI Director (CEO)** | Main Orchestrator | Goal deconstruction, work breakdown, supervision, escalation routing | Level 3 |
| **⚙️ Engineering** | Software Architect | Code synthesis, unit test writing, tool building, debugging | Level 2 |
| **🔬 Research** | Market Intelligence | Web discovery, competitive teardowns, information synthesis, dossier creation | Level 1 |
| **📣 Marketing** | Audience Growth | Multi-channel copy, social campaign staging, content calendar | Level 2 |
| **📊 Analytics** | Performance Officer | KPI tracking, throughput analysis, bottleneck detection, reporting | Level 2 |
| **🔧 Operations** | Infrastructure Hygiene | Recurring sidecars, DB integrity, queue cleanup, system maintenance | Level 2 |
| **🛡️ Quality & Security** | Security Officer | AST static analysis, code safety audits, test verification | Level 2 |

---

## 🛡️ 4-Level Permission Matrix

The organization enforces strict least-privilege security at every layer:

```
Level 1 — Read & Research
  ✓ Read files · analyze data · market intelligence · compute stats
  ✓ No approval needed. Zero write access.

Level 2 — Internal Creation & Sandboxing
  ✓ Create files in agent workspace · build & test code in sandboxes
  ✓ Register internal tools in tool registry

Level 3 — Controlled External Actions  [Director Approval Required]
  ✓ Headless browser automation · staging external API calls
  ✓ Social media queue staging (pre-publish)

Level 4 — Critical & Irreversible Actions  [Human Owner Approval Required]
  ✓ Financial transactions · live external publishing
  ✓ Database destruction · policy file edits
```

> **Security Guarantee:** The AI is strictly barred from modifying `config/permissions.yaml` or bypassing AST sandbox restrictions. All synthesized tools pass zero-tolerance scanning for dangerous calls (`os.system`, `subprocess`, `ctypes`, etc.).

---

## 🏭 The Self-Building Tool Factory

Agents aren't limited to pre-built scripts. When a capability gap is detected, the Tool Factory takes over:

```
1. DISCOVER  →  Agent requests a missing capability (e.g., "regex_keyword_extractor")
2. BUILD     →  Engineering Agent synthesizes pure Python code + comprehensive unit tests
3. SANDBOX   →  Code executes in isolated subprocess with AST safety scanners
4. AUDIT     →  Quality & Security Agent reviews test execution report and risk score
5. REGISTER  →  Approved tools saved to tools_data/ and loaded as callable modules
```

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- pip / virtualenv
- (Optional) Docker & Docker Compose for production

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-company.git
cd ai-company

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your LLM API keys (or leave as 'mock' for offline mode)
```

### 2. Run Locally (Zero API Keys Required)

```bash
# Start the web control center + autonomous background loop
python main.py start
```

Open **http://localhost:8000** for the dark-mode control center.

### 3. CLI Commands

```bash
# Execute one autonomous executive cycle
python main.py cycle

# View live organizational status and agent metrics
python main.py status

# Submit a new strategic business objective
python main.py objective "Launch Competitive Intelligence Scan on AI Tools"
python main.py objective "Write a marketing campaign for Q4" --description "Focus on B2B SaaS"

# Commission the tool factory to build a new tool
python main.py build-tool "web_scraper" "Scrape and parse structured data from a given URL"

# Reset database and workspaces to clean initial state
python main.py reset
```

### 4. Run with Docker Compose (Production)

```bash
# Copy and configure environment
cp .env.example .env
# Add your API keys to .env

# Launch full production stack
docker-compose up -d --build
```

This spins up three containers:
| Container | Purpose |
|---|---|
| `ai_company_orchestrator` | Web server + scheduler + agent worker loop |
| `ai_company_postgres` | Persistent PostgreSQL database |
| `ai_company_redis` | High-throughput task queue and state store |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

```dotenv
# LLM Provider: 'mock' (default, 100% offline), 'openai', 'gemini', 'anthropic', 'ollama'
LLM_PROVIDER=mock

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Google Gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-pro

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Local Ollama (self-hosted models)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Autonomous Execution
AUTO_CYCLE_ENABLED=true
AUTONOMOUS_CYCLE_INTERVAL_SECONDS=15

# Social Media Publishing (optional)
TELEGRAM_BOT_TOKEN=
LINKEDIN_ACCESS_TOKEN=
FACEBOOK_PAGE_ACCESS_TOKEN=
```

---

## 🧠 Supported LLM Providers

| Provider | Key Setting | Default Model | Notes |
|---|---|---|---|
| **Mock** *(default)* | `LLM_PROVIDER=mock` | Built-in simulation | 100% offline, zero API keys |
| **OpenAI** | `LLM_PROVIDER=openai` | `gpt-4o` | Requires `OPENAI_API_KEY` |
| **Google Gemini** | `LLM_PROVIDER=gemini` | `gemini-1.5-pro` | Requires `GEMINI_API_KEY` |
| **Anthropic** | `LLM_PROVIDER=anthropic` | `claude-3-5-sonnet-20241022` | Requires `ANTHROPIC_API_KEY` |
| **Ollama** | `LLM_PROVIDER=ollama` | `llama3` | Self-hosted, no API key needed |

---

## 📁 Project Structure

```
ai-company/
├── agents/                  # Autonomous AI employee agents
│   ├── base.py              #   Base agent class (memory, permissions, LLM)
│   ├── analytics/           #   Analytics & KPI agent
│   ├── engineering/         #   Software engineering agent
│   ├── marketing/           #   Marketing & content agent
│   ├── operations/          #   Operations & maintenance agent
│   ├── quality/             #   Quality & security audit agent
│   └── research/            #   Market research & intelligence agent
├── config/
│   ├── settings.py          # Centralized Pydantic configuration
│   ├── permissions.yaml     # 4-level permission matrix definitions
│   └── company_objectives.yaml
├── dashboard/
│   ├── app.py               # FastAPI application & REST API
│   └── templates/           # Dark-mode HTML control center
├── director/
│   ├── ceo.py               # AI Director: orchestration & supervision
│   ├── delegation.py        # Task decomposition & agent routing
│   ├── cognitive_engine.py  # Strategic reasoning layer
│   └── opportunity_engine.py
├── infrastructure/
│   ├── database.py          # SQLite/PostgreSQL async ORM
│   ├── llm_adapter.py       # Universal multi-provider LLM adapter
│   ├── memory.py            # Episodic + long-term memory store
│   ├── monitoring.py        # Agent health & performance metrics
│   ├── permissions.py       # Permission enforcement engine
│   └── task_queue.py        # Async task queue (in-memory / Redis)
├── integrations/
│   ├── facebook_adapter.py  # Facebook publishing integration
│   ├── linkedin_adapter.py  # LinkedIn publishing integration
│   ├── telegram_adapter.py  # Telegram broadcasting integration
│   └── social_media.py      # Unified social media interface
├── tool_factory/
│   ├── builder.py           # LLM-driven tool code synthesizer
│   ├── registry.py          # Tool registration & versioning
│   └── sandbox.py           # AST safety scanner & isolated executor
├── tests/                   # Unit & integration test suite
├── tools_data/              # Dynamically built & registered agent tools
├── workspace/               # Per-agent private file workspaces
├── .env.example             # Environment configuration template
├── docker-compose.yml       # Production multi-service stack
├── Dockerfile               # Python 3.11 container definition
├── main.py                  # CLI entrypoint
└── requirements.txt         # Python dependencies
```

---

## 🧪 Running Tests

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=. --cov-report=html
```

---

## 🗺️ Roadmap

- [x] Multi-agent hierarchy with CEO director
- [x] 4-level permission enforcement
- [x] Self-building AST-sandboxed tool factory
- [x] Universal multi-LLM adapter (OpenAI, Gemini, Anthropic, Ollama, Mock)
- [x] FastAPI real-time web dashboard
- [x] Persistent episodic + long-term memory per agent
- [x] Telegram / LinkedIn / Facebook social publishing
- [x] Docker + PostgreSQL + Redis production stack
- [ ] Agent-to-agent direct messaging protocol
- [ ] Voice interface for objective submission
- [ ] Browser automation agent (Playwright integration)
- [ ] Plugin marketplace for community-built tools
- [ ] Webhook triggers for CI/CD integration

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## ⭐ Support

If you find this project useful, please give it a ⭐ on GitHub — it helps others discover it!

---

<div align="center">

**Built with 🤖 autonomy and 🧠 intelligence.**

*AI-COMPANY — where AI doesn't just assist, it operates.*

</div>
