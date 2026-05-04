"""Smoke-test retrieval quality against a set of sample queries."""
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.embedding_generator import EmbeddingGenerator
from src.retrieval.in_memory_retrieval import InMemoryRetrieval

EMBEDDINGS_FILE = Path("data/embeddings/policy_embeddings.json")

SAMPLE_QUERIES = [
    "access control policy",
    "incident response procedures",
    "change management controls",
]


def main():
    if not EMBEDDINGS_FILE.exists():
        print(f"Embeddings file not found: {EMBEDDINGS_FILE}")
        print("Run scripts/generate_embeddings.py first.")
        return

    with open(EMBEDDINGS_FILE) as f:
        records = json.load(f)

    generator = EmbeddingGenerator()
    retrieval = InMemoryRetrieval(embedding_generator=generator)
    retrieval.add_documents([{"text": r["text"], "metadata": {"source": r["source"]}} for r in records])

    for query in SAMPLE_QUERIES:
        print(f"\nQuery: {query}")
        results = retrieval.query(query, top_k=3)
        for r in results:
            print(f"  [{r['score']:.3f}] {r['metadata']['source']} — {r['text'][:80]}...")


if __name__ == "__main__":
    main()
