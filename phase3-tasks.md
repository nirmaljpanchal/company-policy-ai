# Phase 3 — Ingestion — Detailed Tasks

Secure, admin-only document ingestion for PolicyChat. Replaces the old
Streamlit/Pinecone upload path with a server-side pipeline: validate → load →
chunk → embed (OpenAI) → store in pgvector. Each task has a goal, deliverables,
and a ready-to-use prompt that can be executed in isolation. See `PLAN.md` for
the full architecture; builds on `phase1-tasks.md` (DB) and `phase2-tasks.md`
(auth/RBAC).

**Stack recap:** FastAPI + SQLAlchemy, Postgres + pgvector, OpenAI
`text-embedding-3-small` (1536-dim). All endpoints admin-only via `require_admin`.

**Execution order:** 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7 → 3.8

---

## Task 3.1 — Upload safety / validation
**Goal:** Reject unsafe or malformed uploads before any processing.
**Deliverables:** `app/security/upload.py`.

**Prompt:**
> Create `backend/app/security/upload.py`. Implement `validate_upload(filename,
> content_bytes, content_type)` that enforces: extension allowlist (`.pdf`,
> `.docx`, `.doc`), MIME allowlist cross-checked against the extension (reject on
> mismatch), a max size cap (configurable, default 10 MB), and non-empty content.
> Sniff the magic bytes (PDF `%PDF`, DOCX zip `PK`) to confirm the real type rather
> than trusting the client. Raise a typed `UploadValidationError` with a clear
> message on any failure. Never execute or eval uploaded content. Add
> `MAX_UPLOAD_MB` to settings.

---

## Task 3.2 — Document processor (load + chunk)
**Goal:** Port the existing loader/chunker into the backend, unchanged in spirit.
**Deliverables:** `app/rag/document_processor.py`.

**Prompt:**
> Create `backend/app/rag/document_processor.py` based on the existing
> `src/document_processor.py`: `load_document(path)` using PyMuPDFLoader for PDF and
> Docx2txtLoader for DOCX/DOC, and `chunk_documents(docs, chunk_size=500,
> chunk_overlap=50)` using RecursiveCharacterTextSplitter, plus `process_file(path)
> -> list[Document]`. Add a helper that accepts raw bytes + filename, writes to a
> NamedTemporaryFile with the right suffix, processes, and always cleans up the temp
> file in a finally block. Return LangChain `Document` chunks.

---

## Task 3.3 — OpenAI embeddings service
**Goal:** Centralized embedding calls with the right model/dimension.
**Deliverables:** `app/rag/embeddings.py`.

**Prompt:**
> Create `backend/app/rag/embeddings.py` wrapping the OpenAI SDK. Add
> `embed_texts(texts: list[str]) -> list[list[float]]` and `embed_query(text: str)
> -> list[float]` using `settings.OPENAI_EMBED_MODEL` (text-embedding-3-small,
> 1536-dim). Batch inputs (respect a sane batch size, e.g. 100), handle empty
> input, and surface API errors clearly. Assert each returned vector length equals
> `settings.EMBED_DIM`. Use a single shared OpenAI client.

---

## Task 3.4 — Persist chunks to pgvector
**Goal:** Store the document record + embedded chunks transactionally.
**Deliverables:** `app/rag/vector_store.py` (replaces the Pinecone version).

**Prompt:**
> Create `backend/app/rag/vector_store.py` (replacing the old Pinecone
> `src/vector_store.py`). Implement `ingest_document(db, *, filename, uploaded_by,
> department, chunks)`: create a `Document` row (status 'processing'), embed all
> chunk texts via the embeddings service, insert `DocChunk` rows (content,
> source=filename, department, embedding), set status 'ready', and commit — all in
> one transaction; on failure set status 'failed' and roll back. Also implement
> `delete_document(db, document_id)` (cascade deletes chunks). Return the created
> `Document`. No Pinecone imports anywhere.

---

## Task 3.5 — Document schemas
**Goal:** Typed responses for the admin document endpoints.
**Deliverables:** `app/schemas/document.py`.

**Prompt:**
> Create `backend/app/schemas/document.py` with pydantic models: `DocumentOut` (id,
> filename, department, status, uploaded_by, created_at; `from_attributes=True`),
> `DocumentListOut` (items: list[DocumentOut], total: int), and `UploadResponse`
> (document: DocumentOut, chunk_count: int).

---

## Task 3.6 — Admin documents router
**Goal:** Admin-only upload / list / delete endpoints.
**Deliverables:** `app/routers/admin.py`.

**Prompt:**
> Create `backend/app/routers/admin.py` with an APIRouter (prefix `/admin`,
> dependency `require_admin` on all routes): `POST /documents` accepts a multipart
> `UploadFile` + form field `department`, reads bytes, calls `validate_upload`,
> processes via the document processor, ingests via `ingest_document` (uploaded_by
> = current admin), and returns `UploadResponse`; `GET /documents` returns
> `DocumentListOut` (optionally filtered by department, paginated); `DELETE
> /documents/{id}` calls `delete_document` and returns 204 (404 if missing). Write
> `upload` and `delete` rows to `audit_log` with the acting user. Remove the
> temporary `/admin/ping` probe from Phase 2.

---

## Task 3.7 — Wire router + config
**Goal:** Mount the admin router and expose new settings.
**Deliverables:** Updated `app/main.py`, settings additions.

**Prompt:**
> Update `backend/app/main.py` to include the admin router. Ensure `MAX_UPLOAD_MB`,
> chunk size/overlap (if you want them configurable), and the embed settings are
> present in `config.py` and `.env.example`. Confirm CORS still allows the frontend
> origin and that multipart uploads work (python-multipart installed).

---

## Task 3.8 — Tests + verification
**Goal:** Prove the ingestion pipeline end to end.
**Deliverables:** `tests/test_ingestion.py` (+ a tiny fixture PDF/DOCX).

**Prompt:**
> Add `backend/tests/test_ingestion.py` using FastAPI TestClient. Mock the OpenAI
> embeddings service to return deterministic 1536-dim vectors (no live API calls).
> Cover: admin uploads a small valid PDF → 200, document status 'ready',
> chunk_count > 0, chunks persisted with the right `source`/`department`; employee
> upload → 403; oversized file → 422/400; wrong extension or MIME/extension
> mismatch → rejected; `GET /documents` lists it; `DELETE /documents/{id}` removes
> it and its chunks (verify cascade). Run the suite and fix failures.

---

## Phase 3 Definition of Done
- [ ] Upload validation blocks bad extension/MIME/size/empty/magic-byte mismatches
- [ ] Loader + chunker ported; temp files always cleaned up
- [ ] OpenAI embeddings return verified 1536-dim vectors
- [ ] `ingest_document` stores document + chunks transactionally (status lifecycle)
- [ ] Admin-only upload/list/delete endpoints work; uploads + deletes audited
- [ ] No Pinecone references remain
- [ ] Ingestion tests pass with embeddings mocked
