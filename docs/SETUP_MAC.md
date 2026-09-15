# Setup Guide — macOS

> **Purpose:** Step-by-step environment setup for macOS contributors.
> **Audience:** Developers setting up this project on macOS for the first time.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [GETTING_STARTED.md](GETTING_STARTED.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 1. Install Homebrew

If you don't already have it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## 2. Install core tooling

```bash
brew install git python@3.11 node@20 ollama
brew install --cask docker
brew install --cask visual-studio-code
```

Open **Docker.app** once from Applications to finish setup and start the Docker daemon.

## 3. Verify installs

```bash
git --version
python3 --version
node --version
docker --version
ollama --version
```

## 4. Clone the repository

```bash
cd ~/projects        # or wherever you keep code
git clone <repository-url> defence-consulting-intelligence-hub
cd defence-consulting-intelligence-hub
```

## 5. Open in VS Code

```bash
code .
```

Install the recommended extensions when prompted (see [.vscode/extensions.json](../.vscode/extensions.json)).

## 6. Continue with common setup

Follow steps 3 onward in [GETTING_STARTED.md](GETTING_STARTED.md):

```bash
cp .env.example .env

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

In a third terminal:

```bash
ollama pull llama3.1
ollama serve
```

## Apple Silicon (M1/M2/M3/M4) notes

- All tools above run natively on Apple Silicon — no Rosetta required.
- Docker images should be built for `linux/arm64`. If you see `exec format error` when running a container, check [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker-issues) for the multi-arch build flag.
- Ollama uses Apple's Metal acceleration automatically — no configuration needed.

## Common macOS gotchas

- **"python: command not found"** — use `python3` explicitly, or add an alias in `~/.zshrc`: `alias python=python3`.
- **Port already in use (5173, 8000, 11434)** — another process is bound to it. Find and stop it: `lsof -i :8000` then `kill -9 <PID>`.
- **Xcode Command Line Tools missing** — some Python packages need a compiler. Run `xcode-select --install`.

More at [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
