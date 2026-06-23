# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate venv (Git Bash on Windows)
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Architecture

PolicyChat is a RAG (Retrieval-Augmented Generation) app built with LangGraph. Users upload policy PDFs/DOCX files, which are chunked, embedded, and stored in Pinecone. Questions are answered by retrieving relevant chunks and generating a cited response via Gemini.

**Data flow:**
1. User uploads file → `src/document_processor.py` loads + chunks it → `src/vector_store.py` embeds (Gemini `text-embedding-004`) and upserts to Pinecone
2. User asks question → `app.py` invokes the LangGraph in `src/graph.py` with `{question, chat_history}`
3. Graph: `retrieve` node queries Pinecone → `generate` node builds prompt + calls `gemini-2.0-flash` → returns `answer` + `sources`
4. Streamlit renders the answer and sources in the chat UI

**LangGraph graph (`src/graph.py`):**
```
START → retrieve → generate → END
```
State shape: `RAGState` — `question`, `chat_history`, `retrieved_docs`, `answer`, `sources`

## Environment Variables

Required in `.env` (see `.env.example`):
- `GOOGLE_API_KEY` — from Google AI Studio
- `PINECONE_API_KEY` — from pinecone.io
- `PINECONE_INDEX_NAME` — Pinecone index name (default: `policy-chat`, dimension must be **768**)

## Key Files

| File | Role |
|---|---|
| `app.py` | Streamlit UI — file upload, chat rendering, graph invocation |
| `src/graph.py` | LangGraph definition — `retrieve` and `generate` nodes |
| `src/vector_store.py` | Pinecone setup, document upsert, retriever factory |
| `src/document_processor.py` | PDF/DOCX loading and text chunking |
