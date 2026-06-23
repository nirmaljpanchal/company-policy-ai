# company-policy-ai
An AI-powered chat app that lets employees instantly query company policies and get accurate, sourced answers.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-red) ![License](https://img.shields.io/badge/license-MIT-brightgreen)

## Overview

PolicyChat is an internal AI chatbot built with Python and Streamlit. Employees can upload company policy PDFs and instantly ask questions in plain language — the app finds the right section and responds with cited answers powered by Claude.

## Features

- Chat interface for querying company policy documents
- Upload PDF/DOCX policy files via sidebar
- RAG pipeline — embeddings + vector search for accurate retrieval
- Source citations with every answer
- Conversation memory within session
- Simple deployment via Streamlit Cloud

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| UI Framework | Streamlit |
| AI / LLM | Anthropic Claude API |
| Embeddings | sentence-transformers |
| Vector Store | FAISS / ChromaDB |
| PDF Parsing | PyMuPDF / pdfplumber |

## Project Structure