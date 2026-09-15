# DevOps for Beginners

> **Purpose:** Explain every tool and workflow step used in this repository, assuming zero prior experience contributing to a software project.
> **Audience:** New joiners with little or no DevOps/software engineering background (e.g. analysts, junior consultants moving into a technical contributor role).
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [GETTING_STARTED.md](GETTING_STARTED.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [../CONTRIBUTING.md](../CONTRIBUTING.md)

---

This guide assumes you have never contributed to a software project before. Read it top to bottom the first time; use it as a reference afterwards. Nothing here is specific to defence consulting — these are general skills you'll reuse on any software project.

## 1. What is Git?

Git is a **version control system** — it tracks every change made to every file over time, who made it, and why. Instead of emailing "final_v2_FINAL.docx" back and forth, everyone works on the same tracked history, and Git can combine (merge) different people's changes automatically in most cases.

Key ideas:
- A **repository** ("repo") is a project's full history, stored in a hidden `.git` folder.
- A **commit** is a saved snapshot of changes, with a message explaining what and why.
- A **branch** is an independent line of work — you make changes on a branch without affecting anyone else until you merge it back.

## 2. What is GitHub?

GitHub is a website that **hosts** Git repositories online and adds collaboration tools on top: pull requests (proposed changes for review), issues (bug reports/feature requests), and discussions. Git is the tool; GitHub is one place to host and collaborate around repos that use it (GitLab and Bitbucket are alternatives).

## 3. What is Azure DevOps?

Azure DevOps is Microsoft's project management and DevOps platform. In this project we use **Azure DevOps-style work management** (Epics → Features → User Stories → Tasks) to plan and track work — documented in [../epics/](../epics/), [../user-stories/](../user-stories/), and [../tasks/](../tasks/), mirroring what you'd see on an actual Azure DevOps board if/when one is connected.

## 4. What is Docker?

Normally, "it works on my machine" is a real problem — different OS versions, different installed tool versions, etc. **Docker** packages an application and everything it needs to run (exact language version, libraries, OS layer) into a **container** — a lightweight, isolated environment that runs identically anywhere Docker is installed. **Docker Compose** lets you define multiple containers (e.g. backend + frontend + database) and start them all together with one command.

## 5. What is FastAPI?

FastAPI is a Python framework for building web APIs — a program that listens for HTTP requests (e.g. "get me the list of opportunities") and returns responses (usually as JSON). It's the backend of this project — see `backend/`.

## 6. What is React?

React is a JavaScript/TypeScript library for building user interfaces — the part of the application you see and click on in a browser. It's the frontend of this project — see `frontend/`.

## 7. What is a Python virtual environment?

Different Python projects often need different versions of the same library. A **virtual environment** ("venv") is an isolated folder containing its own copy of Python packages, so this project's dependencies don't clash with any other Python project on your machine. You create one with `python -m venv .venv` and "activate" it before installing/running anything.

## 8. How to clone the repository

"Cloning" means downloading a full copy of the repository (including its history) onto your computer.

```bash
git clone <repository-url> defence-consulting-intelligence-hub
cd defence-consulting-intelligence-hub
```

## 9. How to install dependencies

"Dependencies" are the external libraries the project needs.

Backend (Python):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Frontend (Node/npm):
```bash
cd frontend
npm install
```

## 10. How to start the backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs to see the interactive API documentation.

## 11. How to start the frontend

```bash
cd frontend
npm run dev
```
Open http://localhost:5173 in your browser.

## 12. How to run Docker Compose

Instead of starting the backend and frontend separately, one command can start everything defined in `docker/docker-compose.yml`:

```bash
docker compose -f docker/docker-compose.yml up --build
```

Press `Ctrl+C` to stop. Add `-d` to run in the background ("detached mode").

## 13. How to run tests

Tests are small programs that check other code behaves correctly.

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```
See [TESTING_STRATEGY.md](TESTING_STRATEGY.md) to understand the different kinds of tests in this project.

## 14. How to create a feature branch

Never work directly on `main` — always create your own branch first:

```bash
git checkout main
git pull origin main
git checkout -b feature/US-014-short-description
```

## 15. How to commit changes

A commit is a saved snapshot with a message.

```bash
git status                 # see what's changed
git add path/to/file.py    # stage a specific file (avoid `git add .` until you're confident)
git commit -m "feat(agents): add schema validation to opportunity agent"
```

See [../CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages) for the message format we use.

## 16. How to push changes

"Pushing" uploads your local commits to the remote (GitHub) copy of the repository:

```bash
git push origin feature/US-014-short-description
```
The first time you push a new branch, Git will suggest the exact command (including `-u` to link your local branch to the remote one) — you can copy-paste it.

## 17. How to create a Pull Request

A **Pull Request (PR)** is a request to merge your branch into `main`, with a description of what changed, for teammates to review.

1. Push your branch (step 16).
2. On GitHub, you'll see a prompt to "Compare & pull request" — click it (or go to the repo's "Pull requests" tab → "New pull request").
3. Fill in the [PR template](../.github/PULL_REQUEST_TEMPLATE.md) — what changed, why, how you tested it, and link the related user story/task.
4. Request a review.
5. Once approved and checks pass, merge (usually "Squash and merge").

## 18. How to resolve merge conflicts

A **merge conflict** happens when Git can't automatically combine changes — usually because two people edited the same lines of the same file. Git will mark the conflicting section in the file like this:

```
<<<<<<< HEAD
your version of the line
=======
the other version of the line
>>>>>>> main
```

To resolve it:
1. Open the file, decide what the final content should be (it might be one side, the other, or a combination).
2. Delete the `<<<<<<<`, `=======`, and `>>>>>>>` marker lines.
3. Save the file.
4. `git add <the file>`
5. `git commit` (Git pre-fills a merge commit message — usually fine as-is) or `git merge --continue` if you were mid-rebase.
6. Push.

If you're unsure which version is correct, ask the person whose change you're conflicting with — don't guess on unfamiliar code.

## 19. How to update from main

Regularly bring your branch up to date with the latest `main` to avoid a huge conflict later:

```bash
git checkout main
git pull origin main
git checkout feature/US-014-short-description
git merge main
```
(Some teams prefer `git rebase main` instead of `merge` — either is fine here; ask if the team has a preference for your area of the codebase.)

## 20. Common troubleshooting scenarios

| Problem | What it means | What to do |
|---|---|---|
| `fatal: not a git repository` | You're not inside the cloned folder | `cd defence-consulting-intelligence-hub` |
| `Permission denied (publickey)` on push | Git isn't authenticated to GitHub | Set up [SSH keys](https://docs.github.com/en/authentication) or use HTTPS with a personal access token |
| `Your branch is behind 'origin/main'` | Someone else pushed changes | `git pull origin main` (or see step 19 for your feature branch) |
| `error: failed to push some refs` | Remote has commits you don't have locally | `git pull` first, resolve any conflicts, then push again |
| `command not found: python`/`node`/`docker` | Tool isn't installed or not on PATH | Revisit [GETTING_STARTED.md](GETTING_STARTED.md) and your OS setup guide |
| PR shows unrelated file changes | Your branch is out of date, or you branched from the wrong place | Update from `main` (step 19); if it persists, ask for help rather than force-pushing blindly |

For anything not covered here, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and [FAQ.md](FAQ.md), or ask a teammate — everyone was new to this once.
