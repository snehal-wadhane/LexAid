"""
ingest.py — One-time script. Reads all PDFs from Database/, chunks by section,
embeds with multilingual-e5-small, and stores in ChromaDB.
Run once: python ingest.py
"""

import os
import re
import hashlib
from pathlib import Path

import pymupdf
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv

load_dotenv()

DATABASE_DIR = Path(os.getenv("DATABASE_DIR", r"D:\LexAid\Database"))
CHROMA_DIR   = Path(os.getenv("CHROMA_DIR",   r"D:\LexAid\backend\chroma_db"))
EMBED_MODEL  = "intfloat/multilingual-e5-small"
COLLECTION   = "lexaid_corpus"

# Corpus map — filename -> metadata (skip duplicates & textbook)
ACT_MAP = {
    "Indian Penal Code, 1860.pdf":                                         {"act_name": "Indian Penal Code, 1860",                                       "short": "IPC",         "category": "criminal"},
    "250883_english_01042024.pdf":                                         {"act_name": "Bharatiya Nyaya Sanhita, 2023",                                  "short": "BNS",         "category": "criminal"},
    "Bharatiya_Nagarik_Suraksha_Sanhita,_2023.pdf":                        {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",                       "short": "BNSS",        "category": "criminal"},
    "250882_english_01042024_0.pdf":                                       {"act_name": "Bharatiya Sakshya Adhiniyam, 2023",                              "short": "BSA",         "category": "evidence"},
    "CPA2019.pdf":                                                         {"act_name": "Consumer Protection Act, 2019",                                  "short": "CPA",         "category": "consumer"},
    "RTI-Act_English.pdf":                                                 {"act_name": "Right to Information Act, 2005",                                 "short": "RTI",         "category": "administrative"},
    "AA2012-32.pdf":                                                           {"act_name": "Protection of Children from Sexual Offences Act, 2012",          "short": "POCSO",       "category": "criminal"},
    "scst-(prevention-of-atrocities)-act,-2015.pdf":                       {"act_name": "SC/ST (Prevention of Atrocities) Act, 1989",                     "short": "SC/ST Act",   "category": "civil_rights"},
    "RPWD-ACT-2016.pdf":                                                   {"act_name": "Rights of Persons with Disabilities Act, 2016",                  "short": "RPWD",        "category": "disability"},
    "20250414714956973.pdf":                                               {"act_name": "Industrial Disputes Act, 1947",                                  "short": "IDA",         "category": "labour"},
    "The_Minimum_Wages_Act.pdf":                                           {"act_name": "Minimum Wages Act, 1948",                                        "short": "MWA",         "category": "labour"},
    "202509111900892266.pdf":                                              {"act_name": "Maharashtra Rent Control Act, 1999",                             "short": "MRCA",        "category": "property"},
    "20240716890312078.pdf":                                               {"act_name": "Constitution of India (as on 1 May 2024)",                        "short": "Constitution","category": "constitutional"},
    "202504081796627129.pdf":                                              {"act_name": "Legal Services Authorities Act, 1987",                           "short": "LSAA",        "category": "legal_services"},
}


def clean_text(text: str) -> str:
    text = text.replace("\x0c", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def sliding_window(text: str, max_words: int = 600, overlap: int = 60) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def split_into_sections(text: str) -> list[str]:
    """Split Indian statutory text on section/article boundaries."""
    # Remove table of contents (anything before the first CHAPTER or PART)
    toc_match = re.search(r"\n\s*(?:CHAPTER|PART)\s+[IVX1-9]", text)
    if toc_match and toc_match.start() < 4000:
        text = text[toc_match.start():]

    boundary = re.compile(
        r"(?:^|\n)\s*"
        r"(?:Section\s+|Article\s+|Sec\.\s*)?"
        r"(\d{1,3}[A-Z]{0,2})\s*"
        r"[\.—\-]\s*"
        r"(?=[A-Z\(\[])",
        re.MULTILINE,
    )
    positions = [m.start() for m in boundary.finditer(text)]

    if len(positions) < 3:
        return sliding_window(text)

    sections = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        chunk = text[pos:end].strip()
        if len(chunk.split()) >= 40:
            sections.append(chunk)

    # Merge very small sections with the next one
    merged, buf = [], ""
    for s in sections:
        buf = (buf + " " + s).strip() if buf else s
        if len(buf.split()) >= 80:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] += " " + buf
        else:
            merged.append(buf)

    return merged if merged else sliding_window(text)


def extract_text(pdf_path: Path) -> str:
    doc = pymupdf.open(str(pdf_path))
    return clean_text("\n".join(p.get_text() for p in doc))


def ingest_all():
    print(f"Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION)
        print("Dropped existing collection")
    except Exception:
        pass

    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    total = 0

    for filename, meta in ACT_MAP.items():
        path = DATABASE_DIR / filename
        if not path.exists():
            print(f"  SKIP (missing): {filename}")
            continue

        print(f"\n→ {meta['act_name']}")
        text = extract_text(path)
        sections = split_into_sections(text)
        print(f"  {len(sections)} chunks")

        # e5 models need "passage: " prefix for indexed documents
        embeddings = model.encode(
            [f"passage: {s}" for s in sections],
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

        ids, docs, metas, embeds = [], [], [], []
        for i, (sec, emb) in enumerate(zip(sections, embeddings)):
            ids.append(hashlib.md5(f"{filename}_{i}".encode()).hexdigest()[:16])
            docs.append(sec[:8000])
            metas.append({
                "act_name": meta["act_name"],
                "short":    meta["short"],
                "category": meta["category"],
                "chunk_idx": i,
                "source":   filename,
            })
            embeds.append(emb.tolist())

        for b in range(0, len(ids), 100):
            col.add(
                ids=ids[b:b+100],
                documents=docs[b:b+100],
                metadatas=metas[b:b+100],
                embeddings=embeds[b:b+100],
            )
        total += len(ids)
        print(f"  ✓ inserted {len(ids)}")

    print(f"\n✅ Done. Total chunks in DB: {total}")
    print(f"   Stored at: {CHROMA_DIR}")


if __name__ == "__main__":
    ingest_all()
