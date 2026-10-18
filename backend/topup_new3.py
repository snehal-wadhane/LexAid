"""
topup_new3.py — Add 3 new acts to existing ChromaDB without wiping it.
  1. IPC 1860 (text-based)  — 1742378582_Indian_Penal_Code_1860.pdf
  2. NI Act 1881             — NI.pdf
  3. PWDVA 2005              — domviolence.pdf
"""

import hashlib
from pathlib import Path
from ingest import (
    DATABASE_DIR, CHROMA_DIR, EMBED_MODEL, COLLECTION,
    extract_text, split_into_sections,
)
from sentence_transformers import SentenceTransformer
import chromadb

NEW_FILES = {
    "1742378582_Indian_Penal_Code_1860.pdf": {
        "act_name": "Indian Penal Code, 1860",
        "short": "IPC", "category": "criminal",
    },
    "NI.pdf": {
        "act_name": "Negotiable Instruments Act, 1881",
        "short": "NIA", "category": "commercial",
    },
    "domviolence.pdf": {
        "act_name": "Protection of Women from Domestic Violence Act, 2005",
        "short": "PWDVA", "category": "civil_rights",
    },
}

print(f"Loading embedding model: {EMBED_MODEL}")
model = SentenceTransformer(EMBED_MODEL)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
col = client.get_collection(COLLECTION)
print(f"Collection '{COLLECTION}' has {col.count()} chunks before topup\n")

total_added = 0
for filename, meta in NEW_FILES.items():
    path = DATABASE_DIR / filename
    if not path.exists():
        print(f"SKIP (missing): {filename}")
        continue

    print(f"→ {meta['act_name']}")
    text = extract_text(path)
    sections = split_into_sections(text)
    print(f"  {len(sections)} chunks")

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
    total_added += len(ids)
    print(f"  ✓ inserted {len(ids)}\n")

print(f"✅ Done. Added {total_added} chunks.")
print(f"   Collection now has {col.count()} total chunks.")
