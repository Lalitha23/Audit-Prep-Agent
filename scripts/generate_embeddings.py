"""
Generate and persist embeddings for all synthetic policy PDFs.

Processes every PDF in data/synthetic/policies/, chunks the text,
tags chunks with entity metadata, generates OpenAI embeddings, and
saves the result to data/embeddings/policy_embeddings.json.

Usage:
    python3 scripts/generate_embeddings.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.pdf_parser import extract_text_from_pdf
from src.utils.chunking import chunk_text, tag_chunk_entities
from src.utils.embedding_generator import generate_embeddings

BASE_DIR      = Path(__file__).parent.parent
POLICIES_DIR  = BASE_DIR / "data" / "synthetic" / "policies"
METADATA_PATH = BASE_DIR / "data" / "synthetic" / "metadata" / "policy_metadata.json"
OUTPUT_DIR    = BASE_DIR / "data" / "embeddings"
OUTPUT_FILE   = OUTPUT_DIR / "policy_embeddings.json"

MODEL         = "text-embedding-3-small"
DIMENSION     = 1536
COST_PER_1K   = 0.00002
WORDS_PER_TOK = 0.75


def _est_tokens(text: str) -> int:
    return max(1, int(len(text.split()) / WORDS_PER_TOK))


def main():
    # ── 0. sanity checks ────────────────────────────────────────────────────
    if not METADATA_PATH.exists():
        print(f"ERROR: metadata not found at {METADATA_PATH}")
        sys.exit(1)

    pdf_files = sorted(POLICIES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"ERROR: no PDF files found in {POLICIES_DIR}")
        sys.exit(1)

    policy_metadata: Dict = json.loads(METADATA_PATH.read_text())

    print("=" * 70)
    print("  Audit Prep Agent — Full Embedding Generation")
    print("=" * 70)
    print(f"  Model         : {MODEL}")
    print(f"  Policies dir  : {POLICIES_DIR}")
    print(f"  Output file   : {OUTPUT_FILE}")
    print(f"  PDFs found    : {len(pdf_files)}")
    print()

    # ── 1. extract, chunk, tag ───────────────────────────────────────────────
    all_tagged: List[Dict] = []
    policies_processed: List[str] = []

    for pdf_path in pdf_files:
        print(f"── {pdf_path.name} {'─' * (50 - len(pdf_path.name))}")

        result = extract_text_from_pdf(str(pdf_path))
        if "error" in result:
            print(f"  ERROR extracting text: {result['error']} — skipping.")
            continue

        chars = len(result["full_text"])
        pages = len(result["pages"])
        print(f"  Extracted : {chars:,} chars across {pages} page(s)")

        chunks = chunk_text(result["full_text"], pdf_path.name)
        tagged = [tag_chunk_entities(c, policy_metadata) for c in chunks]

        est_tok = sum(_est_tokens(c["text"]) for c in tagged)
        print(f"  Chunks    : {len(tagged)}  |  ~{est_tok:,} tokens  |  est. ${est_tok / 1000 * COST_PER_1K:.5f}")

        all_tagged.extend(tagged)
        policies_processed.append(pdf_path.name)
        print()

    if not all_tagged:
        print("ERROR: no chunks to embed.")
        sys.exit(1)

    total_est_tokens = sum(_est_tokens(c["text"]) for c in all_tagged)
    total_est_cost   = total_est_tokens / 1000 * COST_PER_1K
    print(f"Total chunks to embed : {len(all_tagged)}")
    print(f"Total est. tokens     : {total_est_tokens:,}")
    print(f"Total est. cost       : ${total_est_cost:.5f}")
    print()

    # ── 2. generate embeddings ───────────────────────────────────────────────
    print("── Generating embeddings " + "─" * 44)
    t_start = time.time()
    embedded = generate_embeddings(all_tagged, model=MODEL)
    elapsed  = time.time() - t_start

    # ── 3. build output document ─────────────────────────────────────────────
    actual_tokens = sum(_est_tokens(c["text"]) for c in embedded)
    actual_cost   = actual_tokens / 1000 * COST_PER_1K

    output = {
        "metadata": {
            "model":               MODEL,
            "dimension":           DIMENSION,
            "total_chunks":        len(embedded),
            "generated_at":        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "policies_processed":  policies_processed,
        },
        "chunks": embedded,
    }

    # ── 4. save ───────────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    file_kb = OUTPUT_FILE.stat().st_size / 1024

    # ── 5. summary ────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Policies processed : {len(policies_processed)}")
    for name in policies_processed:
        count = sum(1 for c in embedded if c["source"] == name)
        print(f"    • {name} ({count} chunks)")
    print(f"  Total chunks       : {len(embedded)}")
    print(f"  Actual tokens used : {actual_tokens:,}  (est. {total_est_tokens:,})")
    print(f"  Actual cost        : ${actual_cost:.5f}  (est. ${total_est_cost:.5f})")
    print(f"  Elapsed time       : {elapsed:.1f}s")
    print(f"  Output file        : {OUTPUT_FILE}")
    print(f"  File size          : {file_kb:.1f} KB")
    print("=" * 70)


if __name__ == "__main__":
    main()
