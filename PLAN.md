# PolicyChat — Implementation Plan

A company-policy RAG chatbot with admin document management, role-based auth,
per-user daily query quota, and layered security (prompt-injection defense and more).

## Decisions (locked)

| Area | Decision |
|---|---|
| App topology | **Full SPA (React) + FastAPI** backend |
| Auth | **Self-hosted JWT for demo**, pluggable to **Azure Entra ID (OIDC)** later |
| Database | **Postgres** for relational data **and** vectors (`pgvector`) — single store |
| Security | **All** controls: upload safety, input/context injection, prompt hardening, output validation, data isolation, quota, RBAC, audit, secret management |
| LLM | **OpenAI `gpt-4o-mini`** (chat) |
| Embeddings | **OpenAI `text-embedding-3-small`** → **`vector(1536)`** |
| Guardrail | **OpenAI moderation / guardrail model** (e.g. `omni-moderation-latest`) for input + output checks |
| Quota | **5 queries / user / UTC day** |

## What survives from the current code

| Current file | Fate |
|---|---|
| `src/graph.py` (LangGraph retrieve→generate, Gemini) | **Keep structure**, add `guard` node, swap LLM to OpenAI, swap retriever to pgvector |
| `src/document_processor.py` (load + chunk) | **Keep** — runs server-side on admin upload |
| `src/vector_store.py` (Pinecone) | **Replace** with pgvector implementation |
| `app.py` (Streamlit) | **Delete** — replaced by FastAPI routes + React SPA |

The RAG core is reusable; we are replacing storage (Pinecone→pgvector), UI
(Streamlit→React), the model vendor (Gemini→OpenAI), and wrapping it in an
auth + quota + security shell.

## Target stack

**Frontend**
- React + Vite + TypeScript
- React Router, TanStack Query, Tailwind CSS
- Two areas: `/chat` (employee), `/admin` (admin only)

**Backend**
- FastAPI + Uvicorn
- SQLAlchemy 2.x + Alembic migrations
- LangGraph (kept), OpenAI Python SDK
- pydantic-settings for config

**Data**
- Postgres 16 + `pgvector` extension
- Single DB holds users, roles, quota, audit log, documents, and chunk vectors

**Auth**
- `AuthProvider` interface with two implementations:
  - `LocalJWTProvider` (demo): email/password, bcrypt, JWT access + refresh
  - `AzureEntraProvider` (later): validate OIDC tokens, map app roles from claims
- Single `get_current_user()` / `require_role()` dependency — routes don't change when swapping providers

## Repository structure

```
company-policy-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, middleware, routers
│   │   ├── config.py               # settings via pydantic-settings (env / Key Vault)
│   │   ├── db.py                   # engine, session factory, get_db dependency
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py            # pgvector Vector(1536) column
│   │   │   ├── quota.py
│   │   │   └── audit.py
│   │   ├── schemas/                # pydantic request/response models
│   │   ├── auth/
│   │   │   ├── provider.py         # AuthProvider ABC
│   │   │   ├── local_jwt.py        # demo provider
│   │   │   ├── azure_entra.py      # later: OIDC token validation
│   │   │   └── deps.py             # get_current_user, require_role("admin")
│   │   ├── routers/
│   │   │   ├── auth.py             # POST /auth/login, /auth/refresh (demo)
│   │   │   ├── admin.py            # upload, list/delete docs, users, audit
│   │   │   └── chat.py            # POST /chat (quota + guard + RAG)
│   │   ├── rag/
│   │   │   ├── graph.py            # LangGraph: retrieve → guard → generate
│   │   │   ├── vector_store.py     # pgvector retriever (replaces Pinecone)
│   │   │   └── document_processor.py
│   │   ├── security/
│   │   │   ├── moderation.py       # OpenAI moderation/guardrail calls
│   │   │   ├── injection.py        # heuristic input + context injection checks
│   │   │   ├── prompt.py           # hardened system prompt + context delimiting
│   │   │   └── upload.py           # MIME/extension/size validation
│   │   └── services/
│   │       └── quota.py            # atomic per-user/day counter
│   ├── alembic/                    # migrations (incl. CREATE EXTENSION vector)
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/  (Login, Chat, AdminDocs, AdminUsers, AdminAudit)
    │   ├── components/
    │   ├── api/    (typed client, auth interceptor)
    │   └── auth/   (token storage, route guards)
    └── package.json
```

## Database schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- users + roles
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT,                       -- NULL when using Azure Entra
    role          TEXT NOT NULL DEFAULT 'employee',  -- 'admin' | 'employee'
    department    TEXT,
    azure_oid     TEXT UNIQUE,                -- set when provisioned via Entra
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- uploaded documents (metadata)
CREATE TABLE documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename    TEXT NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    department  TEXT,                          -- access-control scope
    status      TEXT NOT NULL DEFAULT 'ready', -- processing | ready | failed
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- chunk vectors
CREATE TABLE doc_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    source      TEXT NOT NULL,                 -- original filename for citation
    department  TEXT,                          -- denormalized for fast filtered search
    embedding   VECTOR(1536) NOT NULL          -- text-embedding-3-small
);

-- HNSW index, cosine distance (matches OpenAI embeddings)
CREATE INDEX doc_chunks_embedding_idx
    ON doc_chunks USING hnsw (embedding vector_cosine_ops);

-- per-user daily quota
CREATE TABLE query_quota (
    user_id    UUID REFERENCES users(id),
    usage_date DATE NOT NULL,
    count      INT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date)
);

-- audit trail
CREATE TABLE audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(id),
    action     TEXT NOT NULL,                  -- 'query' | 'upload' | 'delete' | 'login'
    question   TEXT,
    sources    JSONB,
    ip         TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Access-controlled retrieval (single query)

```sql
SELECT content, source
FROM doc_chunks
WHERE department = ANY(:allowed_departments)   -- access control
ORDER BY embedding <=> :query_embedding         -- cosine similarity
LIMIT 5;
```

One transactional query joins similarity search with the user's allowed scope —
no separate vector store to keep in sync.

## Security controls → implementation

| Control | Where | Detail |
|---|---|---|
| Upload safety | `security/upload.py` | Extension + MIME allowlist (pdf/docx), size cap, reject on mismatch, never execute uploaded content |
| Input moderation | `security/moderation.py` | OpenAI moderation on the user question before processing |
| Input injection | `security/injection.py` | Length cap + heuristic patterns ("ignore previous", role-play, system-prompt probes) |
| Context injection | `security/prompt.py` | Delimit retrieved chunks, instruct model to treat context as **data, not instructions** (spotlighting) |
| Prompt hardening | `security/prompt.py` | Strong system prompt; answer only from context; cite sources or say "I don't know"; refuse out-of-scope/meta requests |
| Output validation | `security/moderation.py` + `graph.py` | OpenAI moderation on generated answer; block leakage of system prompt / disallowed content |
| Data isolation | `rag/vector_store.py` | Retrieval filtered by the caller's `department`/role |
| Quota | `services/quota.py` | Atomic `INSERT ... ON CONFLICT (user_id, usage_date) DO UPDATE SET count = query_quota.count + 1 RETURNING count`; reject when > 5 |
| RBAC | `auth/deps.py` | `require_role("admin")` re-checked server-side on every privileged route; never trust client-sent role |
| Audit | `models/audit.py` | One row per query/upload/delete/login |
| Secrets | `config.py` | Env vars locally; Azure Key Vault in cloud; never in code or client |
| Transport | `main.py` | CORS allowlist, HTTPS in deployment, JWT in Authorization header (not localStorage long-term) |

## Request flow — `POST /chat`

```
1. Verify JWT            → get_current_user()
2. Check role active
3. Quota check + increment (atomic) — reject if > 5/day
4. Input moderation + injection heuristics — reject if flagged
5. Embed question (text-embedding-3-small)
6. Retrieve top-k chunks filtered by user's department
7. Generate with hardened, delimited prompt (gpt-4o-mini)
8. Output moderation/validation
9. Write audit_log row
10. Return { answer, sources, quota_remaining }
```

## LangGraph changes

```
START → retrieve → guard → generate → END
```
- `retrieve`: query pgvector with department filter (was Pinecone)
- `guard`: input moderation + injection check (new node; short-circuits on block)
- `generate`: OpenAI `gpt-4o-mini` with hardened/delimited prompt (was Gemini)
- State `RAGState` gains: `user`, `allowed_departments`, `blocked`, `block_reason`

## API surface (initial)

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/auth/login` | public | Demo login → JWT (removed when Entra is on) |
| POST | `/auth/refresh` | public | Refresh access token |
| GET | `/me` | any | Current user + quota remaining |
| POST | `/chat` | employee+ | Ask a policy question |
| POST | `/admin/documents` | admin | Upload + process a document |
| GET | `/admin/documents` | admin | List documents |
| DELETE | `/admin/documents/{id}` | admin | Delete document + its chunks |
| GET | `/admin/users` | admin | List/manage users |
| GET | `/admin/audit` | admin | View audit log |

## Build order (phased)

1. **Backend skeleton + DB** — FastAPI app, Postgres + pgvector, Alembic baseline migration (incl. `CREATE EXTENSION vector`), SQLAlchemy models, config.
2. **Auth (demo)** — `LocalJWTProvider`, login/refresh, `get_current_user`, `require_role`, seed an initial admin user.
3. **Ingestion** — admin upload → validate → load/chunk → embed (OpenAI) → store chunks (replaces Pinecone path).
4. **RAG + quota + guard** — `POST /chat` full flow with quota, moderation/injection guard, pgvector retrieval, hardened generation, output validation, audit.
5. **React SPA** — login, chat UI (sources + quota counter), admin panel (upload, document list, users, audit).
6. **Azure Entra swap** — implement `AzureEntraProvider` (validate OIDC tokens, map roles from claims), provision users on first login, flip a config switch. No route changes.

## Configuration (`backend/.env.example`)

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/policychat
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_MODERATION_MODEL=omni-moderation-latest
EMBED_DIM=1536
JWT_SECRET=
JWT_ALG=HS256
ACCESS_TOKEN_TTL_MIN=30
REFRESH_TOKEN_TTL_DAYS=7
DAILY_QUERY_LIMIT=5
AUTH_PROVIDER=local            # local | azure_entra
# --- Azure Entra (phase 6) ---
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_JWKS_URL=
```

## Open considerations / future

- **Azure OpenAI** instead of OpenAI public API — keeps LLM, data, and Entra auth in one tenant; same code via the Azure OpenAI endpoint/deployment names.
- **Embedding dimension is fixed at 1536** by `text-embedding-3-small`. Switching to `-large` (3072) later requires a column change + re-embedding all chunks.
- **Streaming responses** for chat (SSE) — nice-to-have after the core flow works.
- **Department/role → document mapping UI** in admin once multi-department access matters.
```
