"""
main.py — FastAPI server for LexAid.
Run: uvicorn main:app --reload --port 8000
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag import stream_answer, retrieve, _get_embed_model, _get_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the embedding model and ChromaDB on startup."""
    loop = asyncio.get_event_loop()
    print("Pre-loading embedding model...")
    await loop.run_in_executor(None, _get_embed_model)
    print("Connecting to ChromaDB...")
    try:
        await loop.run_in_executor(None, _get_collection)
        print("✅ LexAid backend ready")
    except Exception as e:
        print(f"⚠️  ChromaDB not ready (run ingest.py first): {e}")
    yield


app = FastAPI(title="LexAid API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    language: str = "en"
    category: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "LexAid API v0.1"}


@app.post("/api/query")
def query(req: QueryRequest):
    def generate():
        try:
            yield from stream_answer(req.question, category=req.category or None, language=req.language)
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/acts")
def list_acts():
    from ingest import ACT_MAP
    return {
        "acts": [
            {"name": v["act_name"], "short": v["short"], "category": v["category"]}
            for v in ACT_MAP.values()
        ]
    }


@app.post("/api/retrieve")
def retrieve_only(req: QueryRequest):
    """Debug endpoint — returns raw retrieved chunks without LLM."""
    try:
        chunks = retrieve(req.question, category=req.category or None)
        return {"chunks": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
