"""
Test script: validate text chunking and entity tagging for policy PDFs.

Usage:
    python3 scripts/test_chunking.py
"""

import json
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.pdf_parser import extract_text_from_pdf
from src.utils.chunking import chunk_text, tag_chunk_entities

BASE_DIR     = Path(__file__).parent.parent
POLICIES_DIR = BASE_DIR / "data" / "synthetic" / "policies"
METADATA_PATH = BASE_DIR / "data" / "synthetic" / "metadata" / "policy_metadata.json"
TEST_PDF     = "access_control_policy.pdf"


def print_chunk(label: str, chunk: Dict) -> None:
    print(f"\n  [{label}]")
    print(f"    chunk_id   : {chunk['chunk_id']}")
    print(f"    source     : {chunk['source']}")
    print(f"    word_count : {chunk['word_count']}")
    print(f"    char_start : {chunk['char_start']}")
    print(f"    char_end   : {chunk['char_end']}")
    preview = chunk["text"][:120].replace("\n", " ")
    print(f"    text       : {preview!r}{'...' if len(chunk['text']) > 120 else ''}")
    if "entities" in chunk:
        e = chunk["entities"]
        print(f"    entities:")
        print(f"      controls     : {e['controls']}")
        print(f"      framework    : {e['framework']}")
        print(f"      policy_name  : {e['policy_name']}")
        print(f"      evidence_type: {e['evidence_type']}")


def main():
    # --- load metadata ---
    if not METADATA_PATH.exists():
        print(f"ERROR: metadata file not found at {METADATA_PATH}")
        sys.exit(1)
    policy_metadata = json.loads(METADATA_PATH.read_text())
    print(f"Loaded metadata for {len(policy_metadata)} policy file(s).")

    # --- extract text ---
    pdf_path = POLICIES_DIR / TEST_PDF
    result = extract_text_from_pdf(str(pdf_path))
    if "error" in result:
        print(f"ERROR extracting PDF: {result['error']}")
        sys.exit(1)
    print(f"Extracted {len(result['full_text']):,} chars from {TEST_PDF} ({len(result['pages'])} pages).")

    # --- chunk ---
    chunks = chunk_text(result["full_text"], TEST_PDF)
    print(f"\nChunking complete: {len(chunks)} chunk(s) created.")

    # --- tag ---
    tagged = [tag_chunk_entities(c, policy_metadata) for c in chunks]

    # --- report ---
    print("\n" + "=" * 70)
    print_chunk("FIRST CHUNK", tagged[0])
    print_chunk("LAST CHUNK",  tagged[-1])
    print("\n" + "=" * 70)

    # --- verify ---
    failures = []
    for c in tagged:
        if "entities" not in c:
            failures.append(f"{c['chunk_id']}: missing 'entities'")
        elif not c["entities"].get("controls"):
            failures.append(f"{c['chunk_id']}: empty controls list")
        elif not c["entities"].get("framework"):
            failures.append(f"{c['chunk_id']}: missing framework")

    if failures:
        print("VERIFICATION FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print(f"\nVERIFICATION PASSED: all {len(tagged)} chunk(s) have entity metadata.")


if __name__ == "__main__":
    main()
