# Phase 5 — React SPA — Detailed Tasks

The frontend for PolicyChat: a React single-page app with role-gated routing,
a login screen, an employee chat experience (answers + sources + remaining-quota
counter), and an admin panel (document upload/list/delete, user management,
audit log). It talks to the FastAPI backend from Phases 2–4 over JWT. Each task
has a goal, deliverables, and a ready-to-use prompt that can be executed in
isolation.

See `PLAN.md` for the full architecture. Consumes these backend endpoints:
`/auth/login`, `/auth/refresh`, `/me`, `/chat`, `/admin/documents` (GET/POST/DELETE),
`/admin/users`, `/admin/audit`.

**Stack:** React + Vite + TypeScript, React Router, TanStack Query, Tailwind CSS.

**Execution order:** 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 5.9

---

## Task 5.1 — Scaffold frontend
**Goal:** A running Vite + TypeScript app with routing, data fetching, and styling configured.
**Deliverables:** `frontend/` project (Vite React-TS), Tailwind, React Router, TanStack Query.

**Prompt:**
> Create a `frontend/` app using Vite (react-ts template). Add and configure
> Tailwind CSS, React Router (`react-router-dom`), and TanStack Query
> (`@tanstack/react-query` with a `QueryClientProvider` at the root). Set up the
> folder structure from PLAN.md: `src/pages`, `src/components`, `src/api`,
> `src/auth`. Add a `VITE_API_BASE_URL` env var (default `http://localhost:8000`)
> and an `.env.example`. Create a minimal app shell with a router and a placeholder
> route so `npm run dev` serves on port 5173.

---

## Task 5.2 — Typed API client + auth interceptor
**Goal:** One place that talks to the backend, attaches tokens, and refreshes them.
**Deliverables:** `src/api/client.ts`, typed endpoint modules, shared TS types.

**Prompt:**
> In `frontend/src/api/`, create a typed HTTP client (axios or fetch wrapper) using
> `VITE_API_BASE_URL`. Attach the access token as a Bearer header on each request.
> On a 401, attempt a one-time refresh via `/auth/refresh`, retry the original
> request, and on failure clear tokens + redirect to login. Add typed functions:
> `login`, `refresh`, `getMe`, `postChat`, `listDocuments`, `uploadDocument`,
> `deleteDocument`, `listUsers`, `getAudit`. Define shared TypeScript types
> (`User`, `TokenPair`, `ChatResponse`, `DocumentOut`, `AuditEntry`) mirroring the
> backend pydantic schemas.

---

## Task 5.3 — Auth state + route guards
**Goal:** Know who is logged in and gate routes by role.
**Deliverables:** `src/auth/AuthContext.tsx`, token storage, `ProtectedRoute` / `AdminRoute`.

**Prompt:**
> In `frontend/src/auth/`, create an `AuthContext` providing `user`, `login()`,
> `logout()`, and `loading`. Persist tokens (in memory + refresh token in a
> secure-ish store; document the XSS tradeoff and leave a TODO for httpOnly cookies)
> and hydrate `user` on load via `/me`. Add `ProtectedRoute` (requires any
> authenticated user, else redirect to `/login`) and `AdminRoute` (requires
> `user.role === 'admin'`, else redirect to `/chat`). Wire these into the router.

---

## Task 5.4 — Login page
**Goal:** Email/password login against the demo auth backend.
**Deliverables:** `src/pages/Login.tsx`.

**Prompt:**
> Create `frontend/src/pages/Login.tsx`: an email + password form using the
> `AuthContext.login()`, with loading and error states (show a friendly message on
> 401), client-side required-field validation, and redirect to `/chat` on success
> (or `/admin` if the user is an admin). Style with Tailwind. Add a note in the UI
> that this login is replaced by Azure sign-in later.

---

## Task 5.5 — Chat page
**Goal:** The employee experience — ask questions, see cited answers and quota.
**Deliverables:** `src/pages/Chat.tsx` + chat components.

**Prompt:**
> Create `frontend/src/pages/Chat.tsx` with a conversational UI: a scrollable
> message list (user + assistant bubbles), a sources panel/expander under each
> assistant answer (from `ChatResponse.sources`), and an input box. Use a TanStack
> Query mutation calling `postChat`; show a thinking indicator while pending.
> Display a remaining-quota counter (from `quota_remaining`, also fetched from
> `/me`) and disable the input with a clear message when quota is exhausted (handle
> the 429 response). Render a safe refusal message when `blocked` is true. Keep
> chat history in component state and pass it to the request.

---

## Task 5.6 — Admin layout + navigation
**Goal:** A role-gated admin shell hosting the management pages.
**Deliverables:** `src/pages/admin/AdminLayout.tsx`, nav, routes under `/admin`.

**Prompt:**
> Create an admin section under `frontend/src/pages/admin/` wrapped by `AdminRoute`.
> Add `AdminLayout` with a sidebar/nav linking Documents, Users, and Audit, plus a
> header showing the current admin and a logout button. Define nested routes
> `/admin/documents`, `/admin/users`, `/admin/audit`. Style with Tailwind; show the
> employee `/chat` link too so an admin can switch views.

---

## Task 5.7 — Admin documents page
**Goal:** Upload, list, and delete policy documents.
**Deliverables:** `src/pages/admin/Documents.tsx`.

**Prompt:**
> Create `frontend/src/pages/admin/Documents.tsx`. Upload: a file picker (accept
> .pdf/.docx/.doc) + a department field, posting multipart via `uploadDocument`
> with progress/disabled state and client-side size/type pre-checks mirroring the
> backend; show success (filename + chunk_count) or a clear error. List: a
> TanStack Query table of documents (filename, department, status badge,
> created_at) with a delete button that confirms, calls `deleteDocument`, and
> invalidates the query. Handle empty and error states.

---

## Task 5.8 — Admin users + audit pages
**Goal:** Visibility into users and the audit trail.
**Deliverables:** `src/pages/admin/Users.tsx`, `src/pages/admin/Audit.tsx`.

**Prompt:**
> Create `frontend/src/pages/admin/Users.tsx` listing users (email, role,
> department, active) from `listUsers` in a table, and
> `frontend/src/pages/admin/Audit.tsx` listing audit entries (timestamp, user,
> action, question/sources summary, ip) from `getAudit` with simple pagination and
> an action filter. Use TanStack Query, with loading/empty/error states and
> Tailwind styling. (If the backend user-management mutations aren't built yet,
> keep Users read-only and leave a TODO.)

---

## Task 5.9 — Wiring, run scripts, and verification
**Goal:** A cohesive app that builds, runs, and talks to the backend.
**Deliverables:** Router finalization, README, CORS confirmation, smoke test.

**Prompt:**
> Finalize the top-level router (public `/login`; protected `/chat`; admin
> `/admin/*`; redirect `/` based on role; 404 fallback). Add a `frontend/README.md`
> with install/dev/build commands and the `VITE_API_BASE_URL` setup. Confirm the
> backend CORS allowlist includes `http://localhost:5173`. Run `npm run build` to
> verify it type-checks and builds. Do a manual smoke test against the running
> backend: log in as the seeded admin, upload a document, ask a chat question, see
> sources + quota decrement, hit the quota limit, and confirm an employee cannot
> reach `/admin`. Report results.

---

## Phase 5 Definition of Done
- [ ] Vite + TS app runs with Tailwind, Router, and TanStack Query configured
- [ ] Typed API client attaches tokens and auto-refreshes on 401
- [ ] Auth context + ProtectedRoute/AdminRoute gate routes by role
- [ ] Login works against demo auth; redirects by role
- [ ] Chat page shows answers, sources, and a live quota counter; handles 429 + blocked
- [ ] Admin panel: upload/list/delete documents, view users and audit log
- [ ] `npm run build` passes; manual end-to-end smoke test succeeds
