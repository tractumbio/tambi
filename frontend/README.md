# Frontend

> **Purpose:** Explain how to run and navigate the React/TypeScript/MUI frontend application.
> **Audience:** Frontend engineers.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [../architecture/FRONTEND_ARCHITECTURE.md](../architecture/FRONTEND_ARCHITECTURE.md), [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md), [../docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md)

---

## Status

Starter scaffold only — no business functionality implemented yet. The app renders a shell page confirming backend connectivity via `GET /api/v1/health`. See [../README.md#project-status](../README.md#project-status).

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:5173. Requires the backend running on http://localhost:8000 (see [../backend/README.md](../backend/README.md)) — environment variables are read from the repository root [.env](../.env) (copy from [.env.example](../.env.example)), not a separate frontend `.env`.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Vite dev server with hot reload |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | ESLint |
| `npm run type-check` | `tsc --noEmit` |
| `npm test` | Vitest |

## Layout

See [../architecture/FRONTEND_ARCHITECTURE.md](../architecture/FRONTEND_ARCHITECTURE.md) for full rationale.

```
src/
├── api/          Typed API client functions (only place HTTP calls happen)
├── components/    Reusable, presentational components
├── pages/          Route-level views
├── theme/          MUI theme configuration
├── types/           Shared TypeScript types (mirrors backend Pydantic schemas)
├── App.tsx
└── main.tsx
```

## Adding a new page

1. Add a typed API function in `src/api/` if it needs backend data.
2. Add the page component in `src/pages/`.
3. Compose it from `src/components/` where possible rather than one large file.
4. Add a test under `../tests/frontend/`.

See [../docs/CODING_STANDARDS.md#react--typescript](../docs/CODING_STANDARDS.md#react--typescript).
