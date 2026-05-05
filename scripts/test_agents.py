"""
Test script: run the full agent pipeline against the first 3 checklist requirements.

Usage:
    python3 scripts/test_agents.py

Requires ANTHROPIC_API_KEY and OPENAI_API_KEY in .env or the shell environment.
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# Load .env before any src/ imports so API keys are in os.environ at module load time
def _bootstrap_env() -> None:
    from dotenv import load_dotenv
    script_dir = Path(__file__).resolve().parent
    for _ in range(8):
        if (script_dir / ".env").exists():
            load_dotenv(script_dir / ".env", override=False)
            return
        git = script_dir / ".git"
        if git.is_file():
            gitdir = Path(git.read_text().split("gitdir:")[1].strip())
            real_root = gitdir.parent.parent.parent
            if (real_root / ".env").exists():
                load_dotenv(real_root / ".env", override=True)
            return
        if git.is_dir():
            if (script_dir / ".env").exists():
                load_dotenv(script_dir / ".env", override=True)
            return
        script_dir = script_dir.parent

_bootstrap_env()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.in_memory_retrieval import InMemoryRetrieval
from src.agents.coverage_agent import CoverageAgent
from src.agents.orchestrator import OrchestratorAgent

BASE_DIR      = Path(__file__).parent.parent
CHECKLIST_CSV = BASE_DIR / "data" / "synthetic" / "checklists" / "soc2_sample.csv"
TEST_REQS     = 3   # keep API cost low during testing


def load_requirements(path: Path, limit: int) -> List[Dict]:
    reqs = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            reqs.append({
                "requirement_id":    row["requirement_id"],
                "category":          row["category"],
                "requirement_text":  row["requirement_text"],
                "control_objective": row["control_objective"],
            })
    return reqs


def print_gap_report(report: Dict) -> None:
    print("\n" + "=" * 70)
    print("  GAP REPORT SUMMARY")
    print("=" * 70)

    buckets = [
        ("covered", "COVERED",  "Explicit policy coverage found"),
        ("partial",  "PARTIAL",  "Partially addressed — gaps remain"),
        ("at_risk",  "AT RISK",  "Minimal or no coverage found"),
    ]
    for key, label, desc in buckets:
        ids = report.get(key, [])
        marker = "✓" if key == "covered" else ("~" if key == "partial" else "✗")
        print(f"\n  {marker} {label} ({len(ids)}): {', '.join(ids) if ids else 'none'}")

    print("\n" + "-" * 70)
    print("  DETAILS")
    print("-" * 70)

    for req_id, detail in report.get("details", {}).items():
        print(f"\n  {req_id}")
        print(f"    Assessment : {detail.get('assessment')}")
        print(f"    Confidence : {detail.get('confidence')}")
        print(f"    Reasoning  : {detail.get('reasoning', '')}")
        citations = detail.get("citations", [])
        if citations:
            print(f"    Citations  :")
            for c in citations[:2]:
                excerpt = c.get("excerpt", "")[:80].replace("\n", " ")
                print(f"      [{c.get('score', 0):.3f}] {c.get('source')} — {excerpt}...")
        recheck = detail.get("suggested_recheck_terms")
        if recheck:
            print(f"    Recheck terms: {recheck}")

    print("\n" + "=" * 70)


def main() -> None:
    # --- check keys ---
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"ERROR: missing environment variable(s): {', '.join(missing)}")
        print("Add them to your .env file and retry.")
        sys.exit(1)

    print("=" * 70)
    print("  Audit Prep Agent — Agent Pipeline Test")
    print("=" * 70)

    # --- load checklist ---
    requirements = load_requirements(CHECKLIST_CSV, TEST_REQS)
    print(f"\nLoaded {len(requirements)} requirement(s) from checklist:")
    for r in requirements:
        print(f"  • {r['requirement_id']} — {r['category']}")

    # --- build stack ---
    print("\nInitialising retrieval engine...", end=" ", flush=True)
    retrieval = InMemoryRetrieval()
    print(f"loaded {len(retrieval._chunks)} chunks.")

    print("Initialising CoverageAgent...", end=" ", flush=True)
    coverage_agent = CoverageAgent(retrieval_engine=retrieval)
    print("ready.")

    print("Initialising OrchestratorAgent...", end=" ", flush=True)
    orchestrator = OrchestratorAgent(coverage_agent=coverage_agent)
    print("ready.")

    # --- run ---
    gap_report = orchestrator.process_message({"requirements": requirements})

    # --- print report ---
    print_gap_report(gap_report)

    # --- verify ---
    total = len(requirements)
    classified = (
        len(gap_report["covered"]) +
        len(gap_report["partial"]) +
        len(gap_report["at_risk"])
    )
    if classified == total:
        print(f"\n  VERIFICATION PASSED: all {total} requirement(s) classified.\n")
    else:
        print(f"\n  VERIFICATION FAILED: {classified}/{total} classified.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
