# Phase 2 — Auth (Demo) — Detailed Tasks

Demo authentication + role-based access control for PolicyChat, built so the
later Azure Entra ID swap requires no route changes. Each task has a goal,
deliverables, and a ready-to-use prompt that can be executed in isolation.
See `PLAN.md` for the full architecture and `phase1-tasks.md` for the foundation
this builds on.

**Key principle:** all auth/RBAC decisions are made server-side from a validated
token + DB lookup — never from a client-sent role. A single `AuthProvider`
interface lets `LocalJWTProvider` (now) be replaced by `AzureEntraProvider`
(Phase 6) without touching routes.

**Execution order:** 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7 → 2.8

---

## Task 2.1 — Security primitives (hashing + JWT)
**Goal:** Reusable password-hash and token utilities.
**Deliverables:** `app/auth/security.py` — bcrypt hash/verify, JWT encode/decode for access + refresh.

**Prompt:**
> Create `backend/app/auth/security.py`. Using passlib[bcrypt], add
> `hash_password(plain)` and `verify_password(plain, hashed)`. Using python-jose,
> add `create_access_token(subject, role, extra_claims)` and
> `create_refresh_token(subject)` reading TTLs/secret/alg from settings, and
> `decode_token(token)` that validates signature+expiry and returns claims (raise
> a clear error on invalid/expired). Include `sub`, `role`, `type`
> ("access"|"refresh"), `exp`, `iat` claims. No FastAPI imports here — pure
> utilities.

---

## Task 2.2 — AuthProvider interface + LocalJWTProvider
**Goal:** Pluggable auth so Azure Entra swaps in later with no route changes.
**Deliverables:** `app/auth/provider.py` (ABC), `app/auth/local_jwt.py`, factory in `app/auth/__init__.py`.

**Prompt:**
> Create `backend/app/auth/provider.py` defining an `AuthProvider` ABC with
> `authenticate(db, email, password) -> User | None`, `issue_tokens(user) ->
> TokenPair`, `refresh(db, refresh_token) -> TokenPair`, and `identify(db,
> access_token) -> User` (validate token, load user). Then create
> `backend/app/auth/local_jwt.py` with `LocalJWTProvider` implementing it against
> the `User` model using the Task 2.1 utilities: verify password + `is_active`,
> issue access/refresh tokens, validate refresh tokens (reject access tokens used
> as refresh), and load the user by `sub`. Add a `get_auth_provider()` factory in
> `app/auth/__init__.py` that returns the provider based on
> `settings.AUTH_PROVIDER` ("local" now; "azure_entra" raises NotImplementedError
> for now).

---

## Task 2.3 — Auth pydantic schemas
**Goal:** Typed request/response bodies.
**Deliverables:** `app/schemas/auth.py`.

**Prompt:**
> Create `backend/app/schemas/auth.py` with pydantic models: `LoginRequest`
> (email: EmailStr, password: str), `TokenPair` (access_token, refresh_token,
> token_type="bearer"), `RefreshRequest` (refresh_token: str), and `UserOut` (id,
> email, role, department, is_active). Configure `UserOut` with
> `from_attributes=True`.

---

## Task 2.4 — Auth dependencies (get_current_user, require_role)
**Goal:** The single trust boundary every protected route uses.
**Deliverables:** `app/auth/deps.py`.

**Prompt:**
> Create `backend/app/auth/deps.py`. Implement `get_current_user(db, token)` using
> FastAPI `OAuth2PasswordBearer` (or `HTTPBearer`) — extract the bearer token, call
> the active provider's `identify()`, and return the `User`; raise 401 on failure.
> Implement `require_role(*roles)` returning a dependency that calls
> `get_current_user` and raises 403 if `user.role` not in the allowed roles,
> re-checked server-side. Add a convenience `require_admin = require_role("admin")`.
> Never trust a client-sent role — always derive from the validated token + DB.

---

## Task 2.5 — Auth router
**Goal:** Demo login/refresh/me endpoints.
**Deliverables:** `app/routers/auth.py`.

**Prompt:**
> Create `backend/app/routers/auth.py` with an APIRouter (prefix `/auth`):
> `POST /login` (LoginRequest → authenticate via provider → return TokenPair, 401
> on bad creds, write a `login` audit_log row), `POST /refresh` (RefreshRequest →
> provider.refresh → TokenPair), and a `GET /me` (top-level) returning `UserOut`
> for `get_current_user`. Keep login/refresh as demo-only and add a code comment
> that these are disabled when `AUTH_PROVIDER=azure_entra`.

---

## Task 2.6 — Admin seeding
**Goal:** A way to create the first admin without an open registration endpoint.
**Deliverables:** `app/scripts/seed_admin.py` (CLI).

**Prompt:**
> Create `backend/app/scripts/seed_admin.py`, a CLI that reads `--email` and
> `--password` (or env `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD`), opens a DB
> session, and upserts a `User` with role='admin', hashed password, is_active=True
> (idempotent — update if email exists). Print the result. Document the run command
> (`python -m app.scripts.seed_admin --email ... --password ...`) in
> `backend/README.md`. Do not expose a public signup route.

---

## Task 2.7 — Wire router + protect a probe route
**Goal:** Prove the dependency stack works end to end.
**Deliverables:** Updated `app/main.py` including the auth router and a temporary protected route.

**Prompt:**
> Update `backend/app/main.py` to include the auth router and the `/me` route. Add
> a temporary `GET /admin/ping` guarded by `require_admin` that returns
> `{"pong": true, "user": <email>}` to demonstrate RBAC (mark it with a TODO to
> remove once the real admin router lands in Phase 3). Ensure CORS still allows the
> frontend origin.

---

## Task 2.8 — Tests + verification
**Goal:** Confirm auth flows and role enforcement.
**Deliverables:** `tests/test_auth.py`.

**Prompt:**
> Add `backend/tests/test_auth.py` using FastAPI TestClient against the test DB.
> Cover: seed an admin + an employee; login returns tokens; bad password → 401;
> `/me` with a valid access token returns the user; `/me` with no/invalid token →
> 401; refresh returns a new access token; using an access token as a refresh token
> → 401; `/admin/ping` succeeds for admin and returns 403 for employee. Run the
> suite and report results; fix any failures.

---

## Phase 2 Definition of Done
- [ ] Password hashing + JWT access/refresh utilities working
- [ ] `AuthProvider` ABC + `LocalJWTProvider` behind a factory (Entra-ready)
- [ ] `get_current_user` / `require_role` enforce auth + RBAC server-side
- [ ] `/auth/login`, `/auth/refresh`, `/me` functional; login audited
- [ ] First admin seedable via CLI; no public signup
- [ ] All auth tests pass
