"""
app.py - FastAPI backend for Text Validator

This file exposes a minimal FastAPI application that reuses the project's
`src.gemini_analyzer.GeminiAnalyzer` implementation. Start uvicorn from the
project root to ensure imports like `src` resolve correctly.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import os
from typing import Optional

from src.gemini_analyzer import GeminiAnalyzer

_app_analyzer: Optional[GeminiAnalyzer] = None


def get_analyzer() -> GeminiAnalyzer:
    global _app_analyzer
    if _app_analyzer is None:
        use_real = os.environ.get("USE_REAL_GEMINI", "0") == "1"
        _app_analyzer = GeminiAnalyzer(use_real=use_real)
    return _app_analyzer


app = FastAPI(title="Text Validator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/validate")
async def validate_pdf(
    file: UploadFile = File(...),
    start_page: int = Form(1),
    end_page: int = Form(3),
    analyzer: GeminiAnalyzer = Depends(get_analyzer),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF")
    content = await file.read()
    results = await run_in_threadpool(analyzer.analyze_pdf_pages, content, start_page, end_page)
    return {"results": results}