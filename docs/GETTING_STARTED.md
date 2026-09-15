# Getting Started

> **Purpose:** Get a working local development environment up and running as quickly as possible.
> **Audience:** Developers who are comfortable with a terminal and have contributed to software projects before. If this is your first time ever, use [DEVOPS_FOR_BEGINNERS.md](DEVOPS_FOR_BEGINNERS.md) instead.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [SETUP_WINDOWS.md](SETUP_WINDOWS.md), [SETUP_MAC.md](SETUP_MAC.md), [SETUP_LINUX.md](SETUP_LINUX.md), [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 1. Prerequisites

| Tool | Minimum version | Purpose |
|---|---|---|
| [Git](https://git-scm.com/) | 2.40+ | Version control |
| [Python](https://www.python.org/) | 3.11+ | Backend (FastAPI) |
| [Node.js](https://nodejs.org/) | 20 LTS+ | Frontend (React/TypeScript) |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | latest | Containerised local stack |
| [Ollama](https://ollama.com/) | latest | Local LLM runtime for AI agents |
| [VS Code](https://code.visualstudio.com/) | latest | Recommended IDE |

OS-specific installation steps: [SETUP_WINDOWS.md](SETUP_WINDOWS.md) · [SETUP_MAC.md](SETUP_MAC.md) · [SETUP_LINUX.md](SETUP_LINUX.md)

## 2. Clone the repository

```bash
git clone <repository-url> defence-consulting-intelligence-hub
cd defence-consulting-intelligence-hub
```

## 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` — for local development the defaults (Ollama, JSON storage) work out of the box. You do not need OpenAI/Azure OpenAI keys to get started.

## 4. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify: open http://localhost:8000/docs — you should see the FastAPI Swagger UI with a `health` endpoint.

## 5. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Verify: open http://localhost:5173 — you should see the application shell.

## 6. Pull a local model for Ollama

```bash
ollama pull llama3.1
ollama serve
```

## 7. (Optional) Run the full stack with Docker Compose

```bash
docker compose -f docker/docker-compose.yml up --build
```

This starts backend, frontend, and (when enabled) PostgreSQL in one command. See [docker/README.md](../docker/README.md).

## 8. Run the tests

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

See [TESTING_STRATEGY.md](TESTING_STRATEGY.md) for the full testing approach.

## 9. Open the project in VS Code

```bash
code .
```

Install the recommended extensions when prompted (defined in [.vscode/extensions.json](../.vscode/extensions.json)).

## 10. Next steps

- Read [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for the day-to-day workflow.
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand how the pieces fit together.
- Read [CODING_STANDARDS.md](CODING_STANDARDS.md) before writing code.
- Pick up a task from [tasks/](../tasks/) or [sprint-planning/SPRINT_0.md](../sprint-planning/SPRINT_0.md).

Stuck? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or [FAQ.md](FAQ.md).
