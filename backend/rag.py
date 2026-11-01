"""
rag.py — Retrieval + streaming generation.
Loaded once by main.py; model & collection are module-level singletons.
"""

import json
import os
from pathlib import Path
from typing import Generator, Optional

from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

CHROMA_DIR  = Path(os.getenv("CHROMA_DIR", r"D:\LexAid\backend\chroma_db"))
EMBED_MODEL = "intfloat/multilingual-e5-small"
COLLECTION  = "lexaid_corpus"
GROQ_MODEL         = "openai/gpt-oss-120b"
GROQ_MODEL_FALLBACK = "openai/gpt-oss-20b"
TOP_K       = 6

# Keyword → category routing so casual queries skip the wrong acts
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "property":     ["rent", "landlord", "tenant", "eviction", "lease", "1rk", "1bhk",
                     "flat", "accommodation", "paying rent", "house rent", "room rent",
                     "security deposit", "notice to vacate", "rental", "monthly rent"],
    "labour":       ["salary", "wage", "wages", "fired", "dismissed", "retrenchment",
                     "employment", "epf", "gratuity", "provident fund", "factory",
                     "worker", "employee", "employer", "overtime", "minimum wage",
                     "job", "termination", "layoff"],
    "consumer":     ["product", "refund", "defective", "consumer", "complaint", "forum",
                     "service deficiency", "goods", "warranty", "purchase", "ecommerce",
                     "amazon", "flipkart", "bank fraud", "insurance claim"],
    "criminal":     ["murder", "theft", "assault", "fir", "police", "arrest", "bail",
                     "crime", "rape", "robbery", "kidnap", "extortion", "bribe",
                     "cheating", "fraud", "harass", "section 498", "dowry"],
    "administrative":["rti", "right to information", "government", "public authority",
                      "information denied", "pio", "appellate authority"],
    "civil_rights": ["domestic violence", "disability", "discrimination", "atrocity",
                     "sc/st", "scheduled caste", "scheduled tribe", "women rights",
                     "protection order", "maintenance order", "shelter home"],
    "commercial":   ["cheque bounce", "cheque dishonour", "promissory note",
                     "bill of exchange", "negotiable instrument", "138 ni act",
                     "demand notice", "dishonoured"],
    "evidence":     ["evidence", "witness", "document", "proof", "admissibility"],
}


def _detect_category(query: str) -> Optional[str]:
    """Return the best-matching category or None if ambiguous."""
    q = query.lower()
    scores: dict[str, int] = {}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in q)
        if hits:
            scores[cat] = hits
    if not scores:
        return None
    best_cat, best_score = max(scores.items(), key=lambda x: x[1])
    # Only auto-filter when the signal is unambiguous (clear winner)
    if best_score >= 1 and list(scores.values()).count(best_score) == 1:
        return best_cat
    return None


_BASE_SYSTEM_PROMPT = """You are LexAid, an Indian legal information assistant. You help ordinary citizens understand their rights under Indian law.

Rules:
1. Answer ONLY from the statutory sections provided below. Do not use outside knowledge.
2. Cite the Act name and section number for every legal point (e.g., "Under Section 14 of the Consumer Protection Act, 2019...").
3. Use simple, plain language — no legal jargon unless unavoidable, and explain it when you use it.
4. If the provided sections don't fully answer the question, say so clearly.
5. Always end your response with this exact disclaimer on its own line:

---
*LexAid provides legal information based on publicly available Indian law. This is not legal advice and does not create a lawyer-client relationship.*"""

_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
}

def _build_system_prompt(language: str) -> str:
    lang = _LANGUAGE_NAMES.get(language, "English")
    if language == "en":
        return _BASE_SYSTEM_PROMPT
    return (
        _BASE_SYSTEM_PROMPT
        + f"\n\n6. IMPORTANT: Respond entirely in {lang}. "
        + "Keep Act names, section numbers, and legal citations in English, "
        + f"but write all explanations and descriptions in {lang}."
    )

_embed_model: Optional[SentenceTransformer] = None
_collection = None
_groq_client: Optional[Groq] = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection(COLLECTION)
    return _collection


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


def retrieve(query: str, k: int = TOP_K, category: Optional[str] = None) -> list[dict]:
    model = _get_embed_model()
    # e5 models need "query: " prefix for retrieval queries
    embedding = model.encode(f"query: {query}", normalize_embeddings=True).tolist()

    # Auto-detect category when caller didn't specify one
    effective_category = category or _detect_category(query)
    where = {"category": effective_category} if effective_category else None
    # Use more chunks when filtered (fewer acts = richer context per act is fine)
    actual_k = min(k + 2, 10) if effective_category else k
    results = _get_collection().query(
        query_embeddings=[embedding],
        n_results=actual_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":     doc,
            "act_name": meta["act_name"],
            "short":    meta["short"],
            "category": meta["category"],
            "score":    round(1 - dist, 4),
        })
    return chunks


def stream_answer(
    question: str,
    category: Optional[str] = None,
    language: str = "en",
) -> Generator[str, None, None]:
    """Yields SSE-formatted strings: sources event, token events, done event."""

    chunks = retrieve(question, k=TOP_K, category=category)
    if not chunks:
        yield f"data: {json.dumps({'type':'error','message':'No relevant statutory sections found for this question.'})}\n\n"
        return

    # Send sources immediately so UI can show them before tokens arrive
    sources = list({c["act_name"] for c in chunks})
    yield f"data: {json.dumps({'type':'sources','sources':sources})}\n\n"

    context_parts = []
    for i, c in enumerate(chunks, 1):
        context_parts.append(f"[Source {i} — {c['act_name']}]\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)

    groq = _get_groq()
    messages = [
        {"role": "system", "content": _build_system_prompt(language)},
        {
            "role": "user",
            "content": (
                f"Relevant statutory sections:\n\n{context}\n\n"
                f"Question: {question}"
            ),
        },
    ]
    try:
        stream = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            stream=True,
        )
    except Exception:
        stream = groq.chat.completions.create(
            model=GROQ_MODEL_FALLBACK,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            stream=True,
        )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield f"data: {json.dumps({'type':'token','text':delta})}\n\n"

    yield f"data: {json.dumps({'type':'done','chunks':[{'act':c['act_name'],'score':c['score']} for c in chunks]})}\n\n"
