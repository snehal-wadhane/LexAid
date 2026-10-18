"""Quick top-up: ingest just the POCSO act into the existing ChromaDB collection."""
import os, hashlib
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv
from ingest import extract_text, split_into_sections, ACT_MAP

load_dotenv()
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", r"D:\LexAid\backend\chroma_db"))

FILENAME = "AA2012-32.pdf"
DATABASE_DIR = Path(os.getenv("DATABASE_DIR", r"D:\LexAid\Database"))
meta = ACT_MAP[FILENAME]

print("Loading embedding model...")
model = SentenceTransformer("intfloat/multilingual-e5-small")

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
col = client.get_collection("lexaid_corpus")

path = DATABASE_DIR / FILENAME
print(f"Processing: {meta['act_name']}")
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
    ids.append(hashlib.md5(f"{FILENAME}_{i}".encode()).hexdigest()[:16])
    docs.append(sec[:8000])
    metas.append({"act_name": meta["act_name"], "short": meta["short"], "category": meta["category"], "chunk_idx": i, "source": FILENAME})
    embeds.append(emb.tolist())

for b in range(0, len(ids), 100):
    col.add(ids=ids[b:b+100], documents=docs[b:b+100], metadatas=metas[b:b+100], embeddings=embeds[b:b+100])

print(f"  ✓ inserted {len(ids)} POCSO chunks")
print(f"  Collection now has {col.count()} total chunks")
