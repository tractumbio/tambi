# Scripts

> **Purpose:** Index the developer setup/utility scripts and explain when to use each.
> **Audience:** All contributors, especially during initial setup.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md), [../docs/DEVOPS_FOR_BEGINNERS.md](../docs/DEVOPS_FOR_BEGINNERS.md)

---

## Scripts

| Script | Platform | Purpose |
|---|---|---|
| [setup.sh](setup.sh) | macOS / Linux / WSL | One-shot local environment setup (venv, backend deps, frontend deps, `.env`) |
| [setup.ps1](setup.ps1) | Windows (PowerShell, native) | Equivalent setup for native Windows (non-WSL) |
| [start-dev.sh](start-dev.sh) | macOS / Linux / WSL | Start backend + frontend together for local development |

These scripts automate the manual steps in [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) — read that document first if you want to understand what each step does, especially if you're new to this (see [../docs/DEVOPS_FOR_BEGINNERS.md](../docs/DEVOPS_FOR_BEGINNERS.md)).

## Running a script

```bash
chmod +x scripts/setup.sh   # first time only
./scripts/setup.sh
```

On Windows (PowerShell):

```powershell
./scripts/setup.ps1
```

## Adding a new script

Keep scripts small and single-purpose; prefer failing loudly (`set -euo pipefail` in bash) over silently continuing past an error. Document any new script in the table above.
