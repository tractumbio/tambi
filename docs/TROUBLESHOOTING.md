# Troubleshooting

> **Purpose:** Collect fixes for common setup and development problems so contributors aren't blocked.
> **Audience:** All contributors, especially those new to the stack.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [GETTING_STARTED.md](GETTING_STARTED.md), [FAQ.md](FAQ.md), [DEVOPS_FOR_BEGINNERS.md](DEVOPS_FOR_BEGINNERS.md)

---

## General

**"It worked yesterday, now it doesn't"**
Pull the latest `main` and reinstall dependencies — a teammate may have changed `requirements.txt` or `package.json`.
```bash
git pull origin main
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

**Port already in use**
```bash
lsof -i :8000        # or :5173, :11434, :5432
kill -9 <PID>
```

## Backend (FastAPI / Python)

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Virtual environment not activated, or deps not installed | `source .venv/bin/activate && pip install -r requirements.txt` |
| `uvicorn: command not found` | venv not activated | Activate the venv, or run `python -m uvicorn app.main:app --reload` |
| Import errors after pulling `main` | Stale venv | Reinstall: `pip install -r requirements.txt --force-reinstall` |
| CORS errors in browser console | Frontend origin not in `CORS_ORIGINS` | Check `.env`, restart backend |

## Frontend (React / TypeScript / Vite)

| Symptom | Likely cause | Fix |
|---|---|---|
| Blank page, console errors | Stale `node_modules` | `rm -rf node_modules package-lock.json && npm install` |
| Type errors after pulling `main` | Backend schema/types changed | Check `frontend/src/types/`, regenerate if applicable |
| `EADDRINUSE` on `npm run dev` | Port 5173 taken | Kill the process or run `npm run dev -- --port 5174` |
| Styles look wrong / MUI theme missing | `ThemeProvider` not wrapping app | Check `frontend/src/main.tsx` |

## Docker

| Symptom | Likely cause | Fix |
|---|---|---|
| `exec format error` | Wrong image architecture (common on Apple Silicon) | Rebuild with `docker compose build --no-cache`, ensure base images support `linux/arm64` |
| `Cannot connect to the Docker daemon` | Docker Desktop / daemon not running | Start Docker Desktop, or `sudo systemctl start docker` on Linux |
| Containers can't reach each other | Using `localhost` instead of service name | Use the Compose service name (e.g. `http://backend:8000`) inside containers |
| Changes not reflected | Stale image layer | `docker compose up --build` |

## Ollama / AI agents

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` to `localhost:11434` | Ollama not running | `ollama serve` |
| Model not found | Model not pulled | `ollama pull llama3.1` |
| Agent responses are slow | Large model on limited hardware | Use a smaller model (e.g. `llama3.1:8b`) for local dev |
| Agent output fails schema validation | Prompt/model drift | Check the agent's JSON schema in [../ai-agents/](../ai-agents/) and the prompt in [../prompts/](../prompts/) |

## Git

**Merge conflicts** — see [DEVOPS_FOR_BEGINNERS.md#resolving-merge-conflicts](DEVOPS_FOR_BEGINNERS.md#how-to-resolve-merge-conflicts).

**Accidentally committed a secret** — do not just delete it in a new commit (it stays in history). Stop, rotate the credential immediately, and contact the core team to help scrub history.

## Windows-specific issues

- **Line ending warnings (`LF will be replaced by CRLF`)** — expected with Git's autocrlf handling; not an error.
- **`python` not found but `python3` works, or vice versa** — use whichever your install provides consistently; consider WSL2 (see [SETUP_WINDOWS.md](SETUP_WINDOWS.md)) to avoid this entirely.
- **Long path errors** — enable long paths: `git config --system core.longpaths true` (run as Administrator).

## Still stuck?

Check [FAQ.md](FAQ.md), then ask the core team — include the exact error message, your OS, and what you already tried.
