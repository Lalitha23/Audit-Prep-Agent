"""
Test script: validate PDF text extraction for all synthetic policy PDFs.

Usage:
    python3 scripts/test_pdf_extraction.py
"""

import sys
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.pdf_parser import extract_text_from_pdf

POLICIES_DIR = Path(__file__).parent.parent / "data" / "synthetic" / "policies"
PREVIEW_CHARS = 200


def main():
    pdf_files = sorted(POLICIES_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"ERROR: No PDF files found in {POLICIES_DIR}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF(s) in {POLICIES_DIR}\n")
    print("=" * 70)

    all_passed = True

    for pdf_path in pdf_files:
        result = extract_text_from_pdf(str(pdf_path))

        print(f"\nFile     : {result['filename']}")

        if "error" in result:
            print(f"  STATUS : FAILED — {result['error']}")
            all_passed = False
            continue

        page_count = len(result["pages"])
        char_count = len(result["full_text"])
        preview = result["full_text"][:PREVIEW_CHARS].replace("\n", " ").strip()

        print(f"  Pages  : {page_count}")
        print(f"  Chars  : {char_count:,}")
        print(f"  Preview: {preview!r}")

        if not result["full_text"].strip():
            print("  STATUS : FAILED — extracted text is empty")
            all_passed = False
        else:
            print("  STATUS : OK")

    print("\n" + "=" * 70)
    if all_passed:
        print(f"RESULT: All {len(pdf_files)} PDF(s) extracted successfully.")
    else:
        print("RESULT: One or more extractions FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
