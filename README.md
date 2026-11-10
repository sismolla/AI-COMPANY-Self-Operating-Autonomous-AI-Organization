# AI-COMPANY: Self-Operating Autonomous AI Organization

**AI-COMPANY** is a self-hosted, multi-agent AI organization architecture designed to operate autonomously under the strategic direction of an **Owner (You)** and managed by an **AI Director (CEO)**.

Rather than relying on one giant monolithic prompt, the organization distributes responsibility across specialized, autonomous AI employees with independent memory, private workspaces, custom tools, permission boundaries, and performance targets.

---

## 🏛️ Architectural Overview

```
                               ┌──────────────┐
                               │  HUMAN OWNER │
                               │    (Board)   │
                               └──────┬───────┘
                                      │ Sets Objectives & Approves Level 4
                                      ▼
                               ┌──────────────┐
                               │    AI CEO    │
                               │  (Director)  │
                               └──────┬───────┘
                                      │ Plans, Supervises, Delegates
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ Engineering │ │  Research   │ │  Marketing  │ │  Analytics  │ │ Operations  │
 │    Agent    │ │    Agent    │ │    Agent    │ │    Agent    │ │    Agent    │
 └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
        │               │               │               │               │
        └───────────────┼───────────────┴───────────────┼───────────────┘
                        ▼                               ▼
                 ┌─────────────┐                 ┌─────────────┐
                 │   Quality   │                 │    Tool     │
                 │ & Security  │◄────────────────┤   Factory   │
                 └─────────────┘                 └─────────────┘
                                      │
               ═══════════════════════╧═══════════════════════
                           SHARED INFRASTRUCTURE
               • SQLite / PostgreSQL Database
               • Persistent Task Queue & Event Bus
               • AST Sandboxed Tool Runner
               • Persistent Sidecar Scheduler
               • Universal LLM Adapter (Hosted & Local)
               • FastAPI Real-Time Owner Control Center
```

---

## 👥 The Autonomous AI Workforce

| Agent | Role | Scope & Tools | Clearance |
| :--- | :--- | :--- | :---: |
| **AI Director (CEO)** | Main Director | Goal deconstruction, work breakdown, supervision, approvals | Level 3 |
| **Engineering** | Software Architect | Software synthesis, script creation, unit testing, tool building | Level 2 |
| **Research** | Market Intelligence | Web discovery, competitive teardowns, information synthesis | Level 1 |
| **Marketing** | Audience Growth | Multi-channel content, copywriting, social campaign staging | Level 2 |
| **Analytics** | Performance Officer | Organization throughput, KPI tracking, bottleneck detection | Level 2 |
| **Operations** | Infrastructure Hygiene | Recurring sidecars, database integrity, queue cleanup | Level 2 |
| **Quality & Security** | Security Officer | AST static analysis, code safety audit, test verification | Level 2 |

---

## 🛡️ Security & 4-Level Permission Matrix

The organization strictly enforces least-privilege security boundaries:

- **Level 1 (Read & Research)**: Read files, analyze data, perform market intelligence, compute stats. No approval needed.
- **Level 2 (Internal Creation & Sandboxing)**: Create files in agent workspace, build code, run sandbox tests, register internal tools.
- **Level 3 (Controlled External Actions)**: Headless browser automation, staging external API calls, posting to social queue. Requires Director approval.
- **Level 4 (Critical & Irreversible Actions)**: Financial transactions, live external publishing, database destruction, policy edits. **Strictly requires Human Owner approval.**

> **Security Rule**: The AI is strictly barred from rewriting `config/permissions.yaml` or bypassing AST sandbox restrictions.

---

## ⚙️ The Self-Building Tool Factory

Agents are not limited to pre-programmed scripts. When a capability gap is detected:
1. **Discover**: An agent requests a missing capability (e.g., `regex_keyword_extractor`).
2. **Build**: The Engineering Agent synthesizes pure Python code and comprehensive unit tests.
3. **Test in Sandbox**: Code executes inside an isolated subprocess with AST safety scanners enforcing zero dangerous calls (`os.system`, `subprocess`, `ctypes`).
4. **Audit**: Quality & Security Agent reviews the test execution report and risk score.
5. **Register**: Approved tools are saved to `tools_data/` and loaded dynamically as callable modules.

---

## 🚀 Quickstart & Usage

### 1. Run Standalone (Zero-Setup Local Dev)
```bash
# Clone or navigate to directory
cd work_agents

# Run single executive autonomous cycle
python main.py cycle

# View live organizational status
python main.py status

# Submit a strategic business objective
python main.py objective "Launch Competitive Intelligence Scan"

# Launch the FastAPI Web Control Center
python main.py start
```
Access the modern dark-mode control center at: **`http://localhost:8000`**

---

### 2. Run with Docker Compose (Production Server)
```bash
docker-compose up -d --build
```
This spins up:
- `ai_company_orchestrator`: Web server, scheduler, and agent worker loop.
- `ai_company_postgres`: Persistent PostgreSQL database.
- `ai_company_redis`: High-throughput task queue and state store.

---

## 🧠 Supported LLM Providers

Configure your provider in `.env` or environment variables:
- `LLM_PROVIDER=mock`: Built-in role-aware intelligent simulation (Runs 100% offline, zero API keys required).
- `LLM_PROVIDER=openai`: OpenAI models (`OPENAI_API_KEY`, `gpt-4o`).
- `LLM_PROVIDER=gemini`: Google Gemini models (`GEMINI_API_KEY`, `gemini-1.5-pro`).
- `LLM_PROVIDER=anthropic`: Anthropic Claude models (`ANTHROPIC_API_KEY`, `claude-3-5-sonnet-20241022`).
- `LLM_PROVIDER=ollama`: Local open-weights models (`OLLAMA_BASE_URL`, `llama3`).

---

## 🧪 Running Automated Tests
```bash
pytest tests/ -v
```
All subsystems are covered by unit and end-to-end integration tests.
