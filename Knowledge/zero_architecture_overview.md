# Zero AI Technical Specification

Zero AI is a futuristic personal desktop assistant inspired by JARVIS.

## Architecture
Zero operates using a modular architecture with three main layers:
1. PySide6 Desktop GUI (HUD, sidebar, chat panel, status bar)
2. Local Python Backend (FastAPI, SQLite, Conversation Store)
3. Knowledge Base RAG System (SQLite FTS5, BM25 ranking, Document Parsers)

## Document Generation
Zero generates verified executive PDF artifacts using Playwright Chromium.
All generated documents are saved in the exports directory with path traversal prevention.
