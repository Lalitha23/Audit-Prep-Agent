"""
Test script: validate embedding generation for the first 3 chunks of one policy PDF.

Usage:
    export OPENAI_API_KEY=sk-...
    python3 scripts/test_embeddings.py

Only 3 chunks are embedded to minimise API cost during development.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.pdf_parser import extract_text_from_pdf
from src.utils.chunking import chunk_text, tag_chunk_entities
from src.utils.embedding_generator import generate_embeddings

BASE_DIR      = Path(__file__).parent.parent
POLICIES_DIR  = BASE_DIR / "data" / "synthetic" / "policies"
METADATA_PATH = BASE_DIR / "data" / "synthetic" / "metadata" / "policy_metadata.json"
TEST_PDF      = "access_control_policy.pdf"
TEST_CHUNKS   = 3   # keep cost minimal during testing
EXPECTED_DIMS = 1536


def main():
    # --- 1. check API key ---
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        # Try loading from .env in the project root
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.")
        print("  Set it with:  export OPENAI_API_KEY=sk-...")
        print("  Or add it to: .env  (OPENAI_API_KEY=sk-...)")
        sys.exit(1)

    print(f"API key found: {api_key[:8]}{'*' * (len(api_key) - 8)}")

    # --- 2. load metadata ---
    policy_metadata: Dict = json.loads(METADATA_PATH.read_text())
    print(f"Loaded metadata for {len(policy_metadata)} policy file(s).")

    # --- 3. extract text ---
    result = extract_text_from_pdf(str(POLICIES_DIR / TEST_PDF))
    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)
    print(f"Extracted {len(result['full_text']):,} chars from {TEST_PDF}.")

    # --- 4. chunk and tag ---
    all_chunks: List[Dict] = chunk_text(result["full_text"], TEST_PDF)
    tagged: List[Dict]     = [tag_chunk_entities(c, policy_metadata) for c in all_chunks]
    sample = tagged[:TEST_CHUNKS]
    print(f"Total chunks: {len(tagged)}  |  Embedding first {len(sample)} for this test.\n")

    # --- 5. generate embeddings ---
    embedded = generate_embeddings(sample)

    # --- 6. report ---
    print("\n" + "=" * 70)
    for chunk in embedded:
        vec = chunk["embedding"]
        print(f"\nchunk_id  : {chunk['chunk_id']}")
        print(f"word_count: {chunk['word_count']}")
        print(f"embedding dims : {len(vec)}")
        print(f"first 10 values: {[round(v, 6) for v in vec[:10]]}")

    # --- 7. verify ---
    print("\n" + "=" * 70)
    failures: List[str] = []
    for chunk in embedded:
        vec = chunk.get("embedding", [])
        if not vec:
            failures.append(f"{chunk['chunk_id']}: embedding is empty")
        elif len(vec) != EXPECTED_DIMS:
            failures.append(
                f"{chunk['chunk_id']}: expected {EXPECTED_DIMS} dims, got {len(vec)}"
            )

    if failures:
        print("VERIFICATION FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print(
        f"\nVERIFICATION PASSED: all {len(embedded)} chunk(s) have "
        f"{EXPECTED_DIMS}-dimensional embeddings."
    )


if __name__ == "__main__":
    main()
