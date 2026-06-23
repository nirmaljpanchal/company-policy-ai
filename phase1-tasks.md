# Phase 1 — Backend Skeleton + DB — Detailed Tasks

Foundation phase for PolicyChat. Each task has a goal, deliverables, and a
ready-to-use prompt that can be executed in isolation. See `PLAN.md` for the
full architecture and locked decisions.

**Stack recap:** FastAPI + SQLAlchemy 2.x + Alembic, Postgres + pgvector,
OpenAI (`gpt-4o-mini`, `text-embedding-3-small` → `vector(1536)`,
`omni-moderation-latest`), demo JWT auth → Azure Entra later.

**Execution order:** 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8
(1.6 and 1.7 can run in parallel).

---

## Task 1.1 — Scaffold backend structure + dependencies
**Goal:** Create the `backend/` skeleton and pin dependencies.
**Deliverables:** Directory tree from PLAN.md, `requirements.txt`, empty `__init__.py` files.

**Prompt:**
> In the `company-policy-ai` repo, create a `backend/` directory following the
> structure in `PLAN.md` (app/, app/models, app/schemas, app/auth, app/routers,
> app/rag, app/security, app/services, alembic/, tests/). Add
> `backend/requirements.txt` pinning: fastapi, uvicorn[standard], sqlalchemy>=2.0,
> alembic, psycopg[binary], pgvector, pydantic-settings, python-jose[cryptography],
> passlib[bcrypt], openai, langgraph, langchain-core, python-multipart, pymupdf,
> docx2txt. Add `__init__.py` files where needed. Don't implement logic yet —
> skeleton only.

---

## Task 1.2 — Configuration + `.env.example`
**Goal:** Centralized typed settings.
**Deliverables:** `app/config.py` (pydantic-settings `Settings`), `backend/.env.example`.

**Prompt:**
> Create `backend/app/config.py` using pydantic-settings with a `Settings` class
> loading from env: DATABASE_URL, OPENAI_API_KEY, OPENAI_CHAT_MODEL (default
> gpt-4o-mini), OPENAI_EMBED_MODEL (default text-embedding-3-small),
> OPENAI_MODERATION_MODEL (default omni-moderation-latest), EMBED_DIM (default
> 1536), JWT_SECRET, JWT_ALG (default HS256), ACCESS_TOKEN_TTL_MIN (30),
> REFRESH_TOKEN_TTL_DAYS (7), DAILY_QUERY_LIMIT (5), AUTH_PROVIDER (default
> "local"), plus the Azure Entra fields. Expose a cached `get_settings()`. Create
> `backend/.env.example` mirroring the variables in PLAN.md with empty secrets.

---

## Task 1.3 — Database connection layer
**Goal:** Engine, session factory, FastAPI `get_db` dependency.
**Deliverables:** `app/db.py` with declarative `Base`, engine from `DATABASE_URL`, `SessionLocal`, `get_db()` generator.

**Prompt:**
> Create `backend/app/db.py` for SQLAlchemy 2.x: a declarative `Base`, an engine
> built from `Settings.DATABASE_URL` (psycopg driver), a `SessionLocal`
> sessionmaker, and a `get_db()` dependency generator that yields a session and
> closes it. Use `pool_pre_ping=True`.

---

## Task 1.4 — SQLAlchemy models
**Goal:** ORM models matching the PLAN.md schema, including the pgvector column.
**Deliverables:** `app/models/{user,document,chunk,quota,audit}.py`.

**Prompt:**
> Create SQLAlchemy 2.x models in `backend/app/models/` matching the schema in
> PLAN.md: `User` (id UUID PK, email unique, password_hash nullable, role default
> 'employee', department, azure_oid unique nullable, is_active, created_at),
> `Document` (id, filename, uploaded_by FK→users, department, status default
> 'ready', created_at), `DocChunk` (id, document_id FK→documents ON DELETE
> CASCADE, content, source, department, embedding using
> `pgvector.sqlalchemy.Vector(1536)`), `QueryQuota` (composite PK
> user_id+usage_date, count), `AuditLog` (id, user_id FK, action, question,
> sources JSONB, ip, created_at). Use `Mapped`/`mapped_column` typing and UUID PKs
> with server default `gen_random_uuid()`. Import all models in
> `app/models/__init__.py`.

---

## Task 1.5 — Alembic setup + baseline migration
**Goal:** Migrations wired to models; first migration creates extensions, tables, and the HNSW index.
**Deliverables:** `alembic.ini`, `alembic/env.py` (uses `Base.metadata` + `DATABASE_URL`), one baseline migration.

**Prompt:**
> Initialize Alembic in `backend/`. Configure `alembic/env.py` to read
> `DATABASE_URL` from settings and target `app.db.Base.metadata` (import all
> models so they register). Create a baseline migration that first runs
> `CREATE EXTENSION IF NOT EXISTS vector;` and
> `CREATE EXTENSION IF NOT EXISTS pgcrypto;`, then creates all tables, then creates
> the HNSW cosine index
> `doc_chunks_embedding_idx ON doc_chunks USING hnsw (embedding vector_cosine_ops)`.
> Ensure `downgrade()` reverses them. Don't rely on autogenerate for the
> extensions/index — write them explicitly.

---

## Task 1.6 — FastAPI app entrypoint
**Goal:** Bootable app with health check and CORS.
**Deliverables:** `app/main.py`.

**Prompt:**
> Create `backend/app/main.py`: a FastAPI app with a title, CORS middleware (allow
> the frontend origin from settings, default http://localhost:5173), a
> `GET /health` endpoint returning `{"status":"ok"}` plus a DB connectivity check
> (run `SELECT 1`), and router include stubs commented out for auth/admin/chat (to
> be added in later phases). Configure for `uvicorn app.main:app --reload`.

---

## Task 1.7 — Local Postgres + pgvector (docker-compose)
**Goal:** One-command local DB with the extension available.
**Deliverables:** `backend/docker-compose.yml` using a pgvector-enabled Postgres image.

**Prompt:**
> Create `backend/docker-compose.yml` running `pgvector/pgvector:pg16` with a named
> volume, env for db/user/password matching the default DATABASE_URL in
> `.env.example`, port 5432 exposed, and a healthcheck. Add a short "Local DB"
> section to a `backend/README.md` with the up/down commands and the Alembic
> upgrade command.

---

## Task 1.8 — Verify the foundation
**Goal:** Prove phase 1 works end to end before building on it.
**Deliverables:** A working `alembic upgrade head` against the running DB and a passing `/health`.

**Prompt:**
> Bring up the Postgres container, run `alembic upgrade head`, and confirm all
> tables + the `vector` extension + the HNSW index exist (query `\d doc_chunks` /
> pg_extension / pg_indexes). Start the API with uvicorn and confirm `GET /health`
> returns ok with the DB check passing. Report any errors and fix them. Add a
> minimal `tests/test_health.py` using FastAPI TestClient.

---

## Phase 1 Definition of Done
- [ ] `backend/` structure and `requirements.txt` in place
- [ ] `config.py` loads all settings; `.env.example` documented
- [ ] DB session layer + `get_db` dependency working
- [ ] All 5 models defined with `Vector(1536)` chunk column
- [ ] `alembic upgrade head` creates extensions, tables, and HNSW index
- [ ] `GET /health` returns ok with DB check passing
- [ ] Postgres+pgvector runs via docker-compose
- [ ] `tests/test_health.py` passes
