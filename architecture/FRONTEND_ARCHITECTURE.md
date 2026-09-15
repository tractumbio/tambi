# Frontend Architecture

> **Purpose:** Describe the structure, patterns, and conventions of the React/TypeScript/MUI application.
> **Audience:** Frontend engineers.
> **Last Updated:** 2026-08-07
> **Version:** 1.0.0
> **Author:** Adrian Cioanca (acebio)
> **Related Documents:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md), [COMPONENT_RELATIONSHIPS.md](COMPONENT_RELATIONSHIPS.md), [../docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md), [../frontend/README.md](../frontend/README.md)

---

## Stack

- **React 18** with functional components and hooks
- **TypeScript** (strict mode)
- **Material UI (MUI) v5** for components and theming
- **Vite** as the build tool / dev server
- **Recharts** and **Plotly** for data visualisation (see [COMPONENT_RELATIONSHIPS.md](COMPONENT_RELATIONSHIPS.md) for when to use which)
- **Vitest + React Testing Library** for tests

## Folder layout

```
frontend/
├── public/                Static assets
├── src/
│   ├── api/                Typed API client functions (one module per backend domain)
│   ├── components/         Reusable, presentational components
│   ├── pages/               Route-level views (composed from components)
│   ├── theme/               MUI theme configuration
│   ├── types/                Shared TypeScript types/interfaces (mirrors backend Pydantic schemas)
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Layering

```
pages/  ──uses──▶  components/  ──uses──▶  MUI primitives
  │
  └──calls──▶  api/  ──calls──▶  backend REST API
```

- **`pages/`**: one per route (e.g. `DashboardPage.tsx`, `OpportunitiesPage.tsx`, `ReportPage.tsx`). Owns data fetching (via `api/`) and layout; delegates rendering detail to `components/`.
- **`components/`**: presentational, reusable, minimal business logic. Receive data via props.
- **`api/`**: typed functions wrapping `fetch`/axios calls to the backend; this is the *only* place HTTP calls should occur.
- **`types/`**: TypeScript interfaces matching backend Pydantic response models — kept in sync manually for now (see [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md); auto-generation from OpenAPI is a future improvement, see [FUTURE_CLOUD_ARCHITECTURE.md](FUTURE_CLOUD_ARCHITECTURE.md)).

## State management

- **Local component state** (`useState`) for UI-only state.
- **React Context** for cross-cutting concerns (theme, current user preferences) — see `frontend/src/theme/`.
- No global state library (Redux/Zustand) is introduced until a concrete need justifies it — avoid premature complexity.
- Server data is not cached client-side beyond the lifetime of the page in the current phase; a data-fetching library (e.g. TanStack Query) is a candidate future addition once the API surface grows (would need an ADR).

## Theming

MUI's theme (`frontend/src/theme/`) centralises colour palette, typography, and spacing. Components should consume theme tokens (`theme.palette.*`, `theme.spacing()`) rather than hardcoded values, so a future rebrand or dark-mode addition doesn't require touching every component.

## Visualisation

- **Recharts** for standard, interactive dashboard charts embedded in the app (trend lines, bar charts of opportunity volume, etc.) — lighter weight, more "native React."
- **Plotly** for denser analytical charts (e.g. multi-dimensional comparisons in reports) where its richer chart types and export options are worth the extra bundle size.

## Testing

Component and hook tests live alongside the code or under `tests/frontend/`, using Vitest + React Testing Library, asserting on rendered output/user interaction rather than internals. See [../docs/TESTING_STRATEGY.md](../docs/TESTING_STRATEGY.md).

## Build & deployment

`npm run build` produces a static bundle (`frontend/dist/`), served in production via the Nginx-based frontend container — see [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md) and `docker/`.
