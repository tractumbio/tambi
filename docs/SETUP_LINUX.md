# Setup Guide — Linux

> **Purpose:** Step-by-step environment setup for Linux contributors (Ubuntu/Debian-based, with notes for other distros).
> **Audience:** Developers setting up this project on Linux for the first time.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [GETTING_STARTED.md](GETTING_STARTED.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 1. Install core tooling (Ubuntu/Debian)

```bash
sudo apt update && sudo apt upgrade -y

# Git
sudo apt install -y git

# Python 3.11+
sudo apt install -y python3 python3-venv python3-pip

# Node.js 20 LTS (via nvm — recommended over apt's Node)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

# Docker Engine + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out/in for this to take effect

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

For Fedora/RHEL, use `dnf` in place of `apt`; for Arch, use `pacman`. Package names are the same for Git, Python, and Node; follow Docker's [official install docs](https://docs.docker.com/engine/install/) for your distro.

## 2. Install VS Code

```bash
sudo snap install code --classic
# or download the .deb from https://code.visualstudio.com/
```

## 3. Verify installs

```bash
git --version
python3 --version
node --version
docker --version
docker compose version
ollama --version
```

## 4. Clone the repository

```bash
cd ~/projects
git clone <repository-url> defence-consulting-intelligence-hub
cd defence-consulting-intelligence-hub
code .
```

## 5. Continue with common setup

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

## Common Linux gotchas

- **`docker: permission denied`** — you weren't added to the `docker` group, or haven't logged out/in since being added. Run `groups` to check.
- **Port already in use** — `sudo lsof -i :8000` (or `:5173`, `:11434`) then `kill -9 <PID>`.
- **`python3-venv` missing** — some minimal distros don't ship it by default; install via your package manager as shown above.
- **GPU acceleration for Ollama** — for NVIDIA GPUs, install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) if running Ollama via Docker; native `ollama serve` picks up CUDA automatically if drivers are installed.

More at [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
