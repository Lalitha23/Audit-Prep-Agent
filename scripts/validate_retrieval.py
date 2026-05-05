"""
Validate retrieval quality against targeted SOC 2 queries.

Usage:
    python3 scripts/validate_retrieval.py
"""

import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.in_memory_retrieval import InMemoryRetrieval

QUERIES = [
    {
        "query":    "multifactor authentication",
        "expected": "access_control_policy.pdf",
    },
    {
        "query":    "incident response",
        "expected": "information_security_policy.pdf",
    },
    {
        "query":    "vendor management",
        "expected": "vendor_management_policy.pdf",
    },
]

TOP_K = 3


def print_results(query: str, results: List[Dict]) -> None:
    print(f"\n  Query: \"{query}\"")
    print(f"  {'Rank':<5} {'Score':<8} {'Source':<40} {'Preview'}")
    print(f"  {'-'*4} {'-'*7} {'-'*39} {'-'*40}")
    for rank, r in enumerate(results, 1):
        preview = r["text"][:65].replace("\n", " ").strip()
        controls = r["entities"].get("controls", [])
        print(f"  #{rank:<4} {r['score']:<8.4f} {r['source']:<40} {preview}...")
        if controls:
            print(f"  {'':5} {'':8} {'Controls: ' + ', '.join(controls)}")


def main():
    print("=" * 70)
    print("  Retrieval Validation")
    print("=" * 70)

    print("\nLoading InMemoryRetrieval engine...", end=" ", flush=True)
    engine = InMemoryRetrieval()
    print(f"loaded {len(engine._chunks)} chunks.\n")

    passed = 0
    for test in QUERIES:
        results = engine.retrieve(test["query"], top_k=TOP_K)
        print_results(test["query"], results)

        # Relevance check: expected source should appear in top-3
        sources = [r["source"] for r in results]
        if test["expected"] in sources:
            rank = sources.index(test["expected"]) + 1
            print(f"  PASS — '{test['expected']}' in top-{TOP_K} (rank #{rank})")
            passed += 1
        else:
            print(f"  FAIL — '{test['expected']}' not in top-{TOP_K} results")

    print("\n" + "=" * 70)
    print(f"  Results: {passed}/{len(QUERIES)} queries returned relevant results")
    if passed == len(QUERIES):
        print("  VALIDATION PASSED")
    else:
        print("  VALIDATION FAILED — check retrieval quality")
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
