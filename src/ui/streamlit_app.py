import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# ── env bootstrap (must run before any src/ import) ──────────────────────────
from dotenv import load_dotenv

def _load_env() -> None:
    search = Path(__file__).resolve().parent
    for _ in range(8):
        if (search / ".env").exists():
            load_dotenv(search / ".env", override=True)
            return
        git = search / ".git"
        if git.is_file():
            gitdir = Path(git.read_text().split("gitdir:")[1].strip())
            real_root = gitdir.parent.parent.parent
            if (real_root / ".env").exists():
                load_dotenv(real_root / ".env", override=True)
            return
        if git.is_dir():
            if (search / ".env").exists():
                load_dotenv(search / ".env", override=True)
            return
        search = search.parent

_load_env()

# ── path setup ────────────────────────────────────────────────────────────────
_BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE))

import streamlit as st

from src.retrieval.in_memory_retrieval import InMemoryRetrieval
from src.agents.coverage_agent import CoverageAgent
from src.agents.orchestrator import OrchestratorAgent

# ── constants ─────────────────────────────────────────────────────────────────
CHECKLIST_CSV   = _BASE / "data" / "synthetic" / "checklists" / "soc2_sample.csv"
EMBEDDINGS_JSON = _BASE / "data" / "embeddings" / "policy_embeddings.json"

ACCEPTANCE_CRITERIA = [
    ("PDF ingestion pipeline",              True),
    ("Text chunking with overlap",          True),
    ("Embedding generation (OpenAI)",       True),
    ("Cosine similarity retrieval",         True),
    ("Multi-agent coverage assessment",     True),
    ("Gap report with confidence levels",   True),
]

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AuditPrep Agent — Multi-Agent Audit Gap Analysis",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("AuditPrep Agent")
    st.caption("Multi-Agent SOC 2 Gap Analysis")
    st.divider()

    st.subheader("About")
    st.markdown(
        "This tool uses a multi-agent pipeline to assess how well your "
        "policy documents cover SOC 2 Type II requirements.\n\n"
        "**Stack:**\n"
        "- OpenAI `text-embedding-3-small` for retrieval\n"
        "- Claude Sonnet for coverage assessment\n"
        "- Cosine similarity in-memory search"
    )
    st.divider()

    st.subheader("Acceptance Criteria")
    for label, done in ACCEPTANCE_CRITERIA:
        icon = "✅" if done else "⬜"
        st.markdown(f"{icon} {label}")
    st.divider()

    st.subheader("Resources")
    st.markdown("[GitHub Repository](https://github.com/lalithapammi/audit-prep-agent)")

# ── helpers ───────────────────────────────────────────────────────────────────
def load_requirements() -> List[Dict]:
    rows = []
    with open(CHECKLIST_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "requirement_id":    row["requirement_id"],
                "category":          row["category"],
                "requirement_text":  row["requirement_text"],
                "control_objective": row.get("control_objective", ""),
            })
    return rows


@st.cache_resource(show_spinner="Loading retrieval engine...")
def get_retrieval_engine() -> InMemoryRetrieval:
    return InMemoryRetrieval(embeddings_path=EMBEDDINGS_JSON)


def confidence_badge(level: str) -> str:
    return {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}.get(level, level)


def render_citation(c: Dict, idx: int) -> None:
    source  = c.get("source", "unknown")
    excerpt = c.get("excerpt", "")[:200]
    score   = c.get("score", 0.0)
    with st.expander(f"Citation {idx}: {source}  (score: {score:.3f})"):
        st.markdown(f"> {excerpt}")


# ── main page ─────────────────────────────────────────────────────────────────
st.title("🔍 AuditPrep Agent")
st.subheader("Multi-Agent SOC 2 Audit Gap Analysis")

st.info(
    "**Demo Mode:** Using synthetic SOC 2 checklist (12 requirements) "
    "and 3 pre-loaded policy documents (Access Control, Information Security, Vendor Management).",
    icon="ℹ️",
)

col1, col2, col3 = st.columns(3)
col1.metric("Requirements", "12")
col2.metric("Policy Documents", "3")
col3.metric("Embedding Model", "text-embedding-3-small")

st.divider()

run_btn = st.button("▶ Run Analysis", type="primary", use_container_width=True)

if run_btn:
    # ── validate environment ──────────────────────────────────────────────────
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        st.error(f"Missing environment variable(s): {', '.join(missing)}. Check your .env file.")
        st.stop()

    if not EMBEDDINGS_JSON.exists():
        st.error("Embeddings file not found. Run `python3 scripts/generate_embeddings.py` first.")
        st.stop()

    try:
        requirements = load_requirements()
    except Exception as e:
        st.error(f"Could not load checklist: {e}")
        st.stop()

    total = len(requirements)

    # ── initialise agents ─────────────────────────────────────────────────────
    with st.spinner("Initialising agents..."):
        try:
            retrieval       = get_retrieval_engine()
            coverage_agent  = CoverageAgent(retrieval_engine=retrieval)
            orchestrator    = OrchestratorAgent(coverage_agent=coverage_agent)
        except Exception as e:
            st.error(f"Failed to initialise agents: {e}")
            st.stop()

    # ── run analysis with live progress ───────────────────────────────────────
    st.markdown("### Processing Requirements")
    progress_bar  = st.progress(0)
    status_text   = st.empty()
    results_area  = st.container()

    gap_report: Dict = {"covered": [], "partial": [], "at_risk": [], "details": {}}
    live_results: List[Dict] = []

    for idx, req in enumerate(requirements):
        req_id = req["requirement_id"]
        status_text.markdown(
            f"**Processing requirement {idx + 1}/{total}: `{req_id}`** — "
            f"{req['category']}"
        )
        progress_bar.progress((idx) / total)

        try:
            result = coverage_agent.process_message(req)

            # re-query on low confidence (mirrors orchestrator logic)
            if result.get("confidence") == "low" and result.get("suggested_recheck_terms"):
                recheck_msg = dict(req)
                recheck_msg["recheck_terms"] = result["suggested_recheck_terms"]
                recheck = coverage_agent.process_message(recheck_msg)
                _rank = {"Covered": 2, "Partial": 1, "At Risk": 0}
                _conf = {"high": 2, "medium": 1, "low": 0}
                if (_rank.get(recheck.get("assessment",""),0) + _conf.get(recheck.get("confidence",""),0) >=
                    _rank.get(result.get("assessment",""),0)  + _conf.get(result.get("confidence",""),0)):
                    result = recheck

        except Exception as e:
            result = {
                "requirement_id": req_id,
                "assessment":     "At Risk",
                "confidence":     "low",
                "citations":      [],
                "reasoning":      f"Analysis error: {e}",
            }

        assessment = result.get("assessment", "At Risk")
        bucket = {"Covered": "covered", "Partial": "partial", "At Risk": "at_risk"}.get(
            assessment, "at_risk"
        )
        gap_report[bucket].append(req_id)
        gap_report["details"][req_id] = result
        live_results.append(result)

        # inline status pill
        icon = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(assessment, "❓")
        with results_area:
            st.markdown(
                f"{icon} **{req_id}** — {assessment} "
                f"({confidence_badge(result.get('confidence','?'))})"
            )

    progress_bar.progress(1.0)
    status_text.markdown("**Analysis complete.**")
    st.success(
        f"Processed {total} requirements — "
        f"✅ {len(gap_report['covered'])} covered · "
        f"⚠️ {len(gap_report['partial'])} partial · "
        f"🚨 {len(gap_report['at_risk'])} at risk"
    )

    # ── store in session state ────────────────────────────────────────────────
    st.session_state["gap_report"]  = gap_report
    st.session_state["orchestrator"] = orchestrator
    st.session_state["log"]          = orchestrator.get_message_log()


# ── gap report tabs ───────────────────────────────────────────────────────────
if "gap_report" in st.session_state:
    report = st.session_state["gap_report"]

    st.divider()
    st.markdown("## Gap Report")

    tab_covered, tab_partial, tab_risk = st.tabs([
        f"✅ Covered ({len(report['covered'])})",
        f"⚠️ Partial ({len(report['partial'])})",
        f"🚨 At Risk ({len(report['at_risk'])})",
    ])

    # ── Covered ───────────────────────────────────────────────────────────────
    with tab_covered:
        if not report["covered"]:
            st.info("No requirements fully covered.")
        for req_id in report["covered"]:
            d = report["details"][req_id]
            with st.expander(f"✅ {req_id} — {d.get('assessment')} ({confidence_badge(d.get('confidence','?'))})"):
                st.markdown(f"**Reasoning:** {d.get('reasoning','')}")
                for i, c in enumerate(d.get("citations", [])[:2], 1):
                    render_citation(c, i)

    # ── Partial ───────────────────────────────────────────────────────────────
    with tab_partial:
        if not report["partial"]:
            st.info("No partially-covered requirements.")
        for req_id in report["partial"]:
            d = report["details"][req_id]
            with st.expander(f"⚠️ {req_id} — {d.get('assessment')} ({confidence_badge(d.get('confidence','?'))})"):
                st.markdown(f"**Reasoning:** {d.get('reasoning','')}")
                for i, c in enumerate(d.get("citations", [])[:3], 1):
                    render_citation(c, i)
                recheck = d.get("suggested_recheck_terms")
                if recheck:
                    st.markdown(f"**Suggested recheck terms:** `{'`, `'.join(recheck)}`")

    # ── At Risk ───────────────────────────────────────────────────────────────
    with tab_risk:
        if not report["at_risk"]:
            st.success("No at-risk requirements — great coverage!")
        for req_id in report["at_risk"]:
            d = report["details"][req_id]
            with st.expander(f"🚨 {req_id} — {d.get('assessment')} ({confidence_badge(d.get('confidence','?'))})"):
                st.markdown(f"**Reasoning:** {d.get('reasoning','')}")
                st.markdown("**Suggested next steps:**")
                st.markdown(
                    "- Draft or locate an existing policy that addresses this requirement\n"
                    "- Engage the control owner to document evidence\n"
                    "- Add to remediation backlog with target date"
                )
                for i, c in enumerate(d.get("citations", [])[:2], 1):
                    render_citation(c, i)
                recheck = d.get("suggested_recheck_terms")
                if recheck:
                    st.markdown(f"**Suggested recheck terms:** `{'`, `'.join(recheck)}`")

    # ── export ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Export")

    log_data = st.session_state.get("log", [])
    export_payload = {
        "gap_report":    report,
        "decision_log":  log_data,
    }

    st.download_button(
        label="⬇️ Download Decision Log (JSON)",
        data=json.dumps(export_payload, indent=2),
        file_name="auditprep_decision_log.json",
        mime="application/json",
        use_container_width=True,
    )
