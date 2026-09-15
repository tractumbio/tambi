# Setup Guide — Windows

> **Purpose:** Step-by-step environment setup for Windows 10/11 contributors.
> **Audience:** Developers setting up this project on Windows for the first time.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [GETTING_STARTED.md](GETTING_STARTED.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## Recommended: use WSL2

We strongly recommend running this project inside **WSL2 (Windows Subsystem for Linux)** with Ubuntu, rather than native Windows. Docker, Python, and Node all behave more predictably there, and it matches Linux/macOS teammates' environments.

### 1. Install WSL2

Open PowerShell **as Administrator**:

```powershell
wsl --install -d Ubuntu
```

Restart when prompted, then complete the Ubuntu username/password setup.

### 2. Install Docker Desktop

Download from [docker.com](https://www.docker.com/products/docker-desktop/). During install, enable **"Use WSL2 based engine"**. In Docker Desktop settings, enable integration with your Ubuntu distro (Settings → Resources → WSL Integration).

### 3. Open a WSL terminal and install tooling

```bash
sudo apt update && sudo apt upgrade -y

# Git
sudo apt install -y git

# Python 3.11+
sudo apt install -y python3 python3-venv python3-pip

# Node.js 20 LTS (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### 4. Install VS Code + WSL extension

Install VS Code on Windows normally, then install the **"WSL"** extension (`ms-vscode-remote.remote-wsl`). Open the project from inside WSL:

```bash
cd ~
git clone <repository-url> defence-consulting-intelligence-hub
cd defence-consulting-intelligence-hub
code .
```

VS Code will reopen "in WSL" — this is correct and expected.

### 5. Continue with the common setup

Follow steps 3 onward in [GETTING_STARTED.md](GETTING_STARTED.md) from inside your WSL terminal.

## Alternative: native Windows (not recommended)

If you cannot use WSL2:

1. Install [Git for Windows](https://git-scm.com/download/win).
2. Install [Python 3.11+](https://www.python.org/downloads/windows/) — check **"Add Python to PATH"** during install.
3. Install [Node.js 20 LTS](https://nodejs.org/) using the Windows installer.
4. Install Docker Desktop with the Hyper-V backend.
5. Install Ollama for Windows from [ollama.com](https://ollama.com/download/windows).
6. Use PowerShell or Git Bash for all commands in [GETTING_STARTED.md](GETTING_STARTED.md) — for the Python virtual environment, activate with `.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

Known issues with native Windows are tracked in [TROUBLESHOOTING.md](TROUBLESHOOTING.md#windows-specific-issues).

## Verifying your setup

```powershell
git --version
python --version
node --version
docker --version
ollama --version
```

Each should print a version number without error. If any fail, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
