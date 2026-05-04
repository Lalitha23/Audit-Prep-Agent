"""Pre-compute embeddings for synthetic documents and cache them to disk."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.pdf_parser import parse_pdf
from src.utils.chunking import chunk_text
from src.utils.embedding_generator import EmbeddingGenerator

POLICIES_DIR = Path("data/synthetic/policies")
OUTPUT_DIR = Path("data/embeddings")
OUTPUT_FILE = OUTPUT_DIR / "policy_embeddings.json"


def main():
    generator = EmbeddingGenerator()
    records = []

    for pdf_path in POLICIES_DIR.glob("*.pdf"):
        text = parse_pdf(pdf_path)
        chunks = chunk_text(text)
        embeddings = generator.embed_batch(chunks)
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            records.append({
                "source": pdf_path.name,
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding,
            })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(records, f)

    print(f"Saved {len(records)} chunks to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
