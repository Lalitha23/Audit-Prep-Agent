import csv
import json
import os
import sys
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

_BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BASE))

import streamlit as st

from src.retrieval.in_memory_retrieval import InMemoryRetrieval
from src.agents.coverage_agent import CoverageAgent
from src.agents.orchestrator import OrchestratorAgent

# ── constants ─────────────────────────────────────────────────────────────────
CHECKLIST_CSV    = _BASE / "data" / "synthetic" / "checklists" / "soc2_sample.csv"
EMBEDDINGS_JSON  = _BASE / "data" / "embeddings" / "policy_embeddings.json"

POLICY_NAMES = {
    "access_control_policy.pdf":       "Access Control Policy",
    "information_security_policy.pdf": "Information Security Policy",
    "vendor_management_policy.pdf":    "Vendor Management Policy",
}
ACCEPTANCE_CRITERIA = [
    ("PDF ingestion pipeline",            True),
    ("Text chunking with overlap",        True),
    ("Embedding generation (OpenAI)",     True),
    ("Cosine similarity retrieval",       True),
    ("Multi-agent coverage assessment",   True),
    ("Gap report with confidence levels", True),
]
CONFIDENCE_SCORES = {"high": 1.0, "medium": 0.5, "low": 0.0}

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AuditPrep Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Chat bubble */
.chat-bubble {
    background: #f5f5f5;
    border-radius: 16px;
    border: 1px solid #e0e0e0;
    padding: 20px 24px;
    margin: 12px 0 8px 0;
    font-size: 0.95rem;
    line-height: 1.6;
}
.chat-bubble .doc-list { margin: 8px 0 12px 0; }
.chat-bubble .doc-list p { margin: 2px 0; }
.chat-bubble .user-msg {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #ddd;
    font-style: italic;
    color: #333;
}
/* Red primary button override */
div[data-testid="stButton"] button[kind="primary"] {
    background-color: #dc3545 !important;
    border-color: #dc3545 !important;
    color: white !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 2rem !important;
    border-radius: 8px !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #b02a37 !important;
    border-color: #b02a37 !important;
}
/* Assessment pills */
.pill-covered  { background:#d4edda; color:#155724; border-radius:4px; padding:2px 8px; font-size:0.85rem; }
.pill-partial  { background:#fff3cd; color:#856404; border-radius:4px; padding:2px 8px; font-size:0.85rem; }
.pill-at-risk  { background:#f8d7da; color:#721c24; border-radius:4px; padding:2px 8px; font-size:0.85rem; }
/* Footer */
.footer { text-align:center; color:#aaa; font-size:0.80rem; margin-top:40px; }
</style>
""", unsafe_allow_html=True)

# ── helpers ───────────────────────────────────────────────────────────────────
def load_requirements() -> List[Dict]:
    if not CHECKLIST_CSV.exists():
        raise FileNotFoundError(f"Checklist not found: {CHECKLIST_CSV}")
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

@st.cache_resource(show_spinner="Loading embeddings…")
def get_retrieval_engine() -> InMemoryRetrieval:
    if not EMBEDDINGS_JSON.exists():
        raise FileNotFoundError("Embeddings file not found. Run generate_embeddings.py first.")
    try:
        return InMemoryRetrieval(embeddings_path=EMBEDDINGS_JSON)
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Corrupted embeddings file: {e}")

def confidence_badge(level: str) -> str:
    return {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}.get(level, f"❓ {level}")

def policy_name(filename: str) -> str:
    return POLICY_NAMES.get(filename, filename)

def avg_confidence(details: Dict) -> str:
    scores = [CONFIDENCE_SCORES.get(d.get("confidence","low"), 0) for d in details.values()]
    avg = sum(scores) / len(scores) if scores else 0
    if avg >= 0.75: return "🟢 High"
    if avg >= 0.35: return "🟡 Medium"
    return "🔴 Low"

def render_citation(c: Dict, idx: int) -> None:
    src     = c.get("source", "unknown")
    excerpt = c.get("excerpt", "").strip()[:300]
    score   = c.get("score", 0.0)
    with st.expander(f"📄 {idx}. {policy_name(src)}  (relevance {score:.3f})"):
        st.caption(f"Source file: `{src}`")
        if excerpt:
            st.info(f'"{excerpt}"')

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("AuditPrep Agent")
    st.caption("Multi-Agent SOC 2 Gap Analysis")
    st.divider()

    with st.expander("⚙️ How It Works", expanded=False):
        st.markdown("""
**Pipeline overview**

1. **Orchestrator Agent** receives the checklist and loops over every requirement.

2. **Coverage Agent** handles each requirement:
   - Embeds the requirement text with OpenAI
   - Ranks policy chunks by cosine similarity
   - Sends requirement + top-5 chunks to Claude Sonnet
   - Returns Covered / Partial / At Risk + reasoning

3. **Self-correction** — if confidence is *low*, the Orchestrator re-queries with Claude's own suggested recheck terms and keeps the better result.

4. **Semantic search** — no keyword matching; embeddings capture *meaning*, so "MFA" matches "multi-factor authentication" naturally.
        """)

    st.divider()
    st.subheader("Acceptance Criteria")
    for label, done in ACCEPTANCE_CRITERIA:
        st.markdown(f"{'✅' if done else '⬜'} {label}")
    st.divider()
    st.markdown("[GitHub](https://github.com/lalithapammi/audit-prep-agent)")

# ── page header ───────────────────────────────────────────────────────────────
st.title("🔍 AuditPrep Agent")
st.caption("Multi-Agent SOC 2 Type II Audit Gap Analysis")

# ── PRE-FLIGHT warning ────────────────────────────────────────────────────────
_missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if _missing:
    st.warning(
        f"Missing API key(s): {', '.join(_missing)}. Add to `.env` before running.",
        icon="⚠️",
    )

# ═══════════════════════════════════════════════════════════════════════════════
# LAYOUT — define top→bottom containers; fill them in display order later
# ═══════════════════════════════════════════════════════════════════════════════

# TOP: gap report (empty until analysis completes)
report_area = st.container()

# MIDDLE: agent progress (empty until Start is clicked)
progress_area = st.container()

# BOTTOM: chat message box (always visible)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""---""")
st.markdown("#### Your request")

st.markdown("""
<div class="chat-bubble">
  <div class="doc-list">
    <strong>📎 Uploaded Documents</strong><br>
    <p>✅ &nbsp;<code>soc2_sample.csv</code> &nbsp;—&nbsp; 12 requirements</p>
    <p>✅ &nbsp;<code>access_control_policy.pdf</code></p>
    <p>✅ &nbsp;<code>information_security_policy.pdf</code></p>
    <p>✅ &nbsp;<code>vendor_management_policy.pdf</code></p>
  </div>
  <div class="user-msg">
    "Analyze these documents against SOC 2 and show coverage."
  </div>
</div>
""", unsafe_allow_html=True)

# Centered red Start button
_bcol1, _bcol2, _bcol3 = st.columns([1, 2, 1])
with _bcol2:
    run_btn = st.button(
        "▶ Start Analysis",
        type="primary",
        use_container_width=True,
        disabled=bool(_missing),
        key="run_btn",
    )

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS — runs when button clicked
# ═══════════════════════════════════════════════════════════════════════════════

def _write_req_expander(ph, req_id: str, category: str, lines: List[str],
                        done: bool = False, result: Optional[Dict] = None) -> None:
    """Write/update a single requirement's detail expander into placeholder *ph*.

    During processing (done=False): expander is expanded with live step lines.
    After completion (done=True):   expander collapses with full detail content.
    """
    assessment = (result or {}).get("assessment", "")
    confidence = (result or {}).get("confidence", "")
    requeried  = (result or {}).get("_requeried", False)
    chunks     = (result or {}).get("retrieved_chunks", [])
    citations  = (result or {}).get("citations", [])
    reasoning  = (result or {}).get("reasoning", "")

    if done and assessment:
        icon   = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(assessment, "❓")
        title  = (f"{icon} **{req_id}** — {assessment} "
                  f"({confidence_badge(confidence)})"
                  + (" ↩️" if requeried else ""))
    else:
        title = f"⏳ **{req_id}** — analyzing…"

    with ph.container():
        with st.expander(title, expanded=not done):
            st.caption(category)
            for line in lines:
                st.markdown(line)

            if done and chunks:
                st.markdown("---")
                st.markdown("**🔎 Retrieved evidence chunks:**")
                # Summarise sources
                source_counts: Dict[str, int] = {}
                for c in chunks:
                    src = policy_name(c.get("source", "unknown"))
                    source_counts[src] = source_counts.get(src, 0) + 1
                src_summary = ", ".join(f"{s} ({n})" for s, n in source_counts.items())
                st.caption(f"Sources: {src_summary}")

                # Top chunk preview
                top = chunks[0]
                top_text  = top.get("text", "")[:200].replace("\n", " ")
                top_score = top.get("score", 0.0)
                st.info(f'**Top chunk** (relevance {top_score:.3f}):\n\n"{top_text}…"')

            if done and citations:
                st.markdown("**📄 Citations from Claude:**")
                for i, c in enumerate(citations[:3], 1):
                    render_citation(c, i)

            if done and requeried:
                st.warning(
                    f"↩️ **Re-queried** with: "
                    + ", ".join(f"`{t}`" for t in
                                (result or {}).get("suggested_recheck_terms", []))
                )

            if done and reasoning:
                st.markdown(f"**🧠 Reasoning:**\n\n{reasoning}")


if run_btn:
    for key in ("gap_report", "steps", "decision_log"):
        st.session_state.pop(key, None)

    try:
        requirements = load_requirements()
    except Exception as e:
        st.error(f"**Could not load checklist:** {e}")
        st.stop()

    try:
        retrieval      = get_retrieval_engine()
        coverage_agent = CoverageAgent(retrieval_engine=retrieval)
        orchestrator   = OrchestratorAgent(coverage_agent=coverage_agent)
    except Exception as e:
        st.error(f"**Initialisation error:** {e}")
        st.stop()

    total = len(requirements)
    gap_report: Dict = {"covered": [], "partial": [], "at_risk": [], "details": {}}
    steps: List[Dict] = []

    with progress_area:
        st.markdown("#### 🤖 Agent Activity")

        # ── Initialisation expander ───────────────────────────────────────────
        init_ph = st.empty()
        with init_ph.container():
            with st.expander("🔧 **Orchestrator:** Initializing…", expanded=True):
                st.markdown("Loading embeddings… ✓")
                st.markdown(f"Retrieval engine ready — **{len(retrieval._chunks)} chunks** indexed ✓")
                st.markdown("Initializing Coverage Agent… ✓")
                st.markdown(f"Parsed checklist — **{total} requirements** loaded ✓")

        # ── Create one placeholder per requirement (pre-allocates vertical space) ──
        req_placeholders = {req["requirement_id"]: st.empty() for req in requirements}

        # ── Process each requirement ──────────────────────────────────────────
        for idx, req in enumerate(requirements, 1):
            req_id   = req["requirement_id"]
            category = req["category"]
            ph       = req_placeholders[req_id]

            # --- step 1: show "querying" state ---
            _write_req_expander(ph, req_id, category, [
                "🔎 Querying retrieval system…",
            ], done=False)

            try:
                result    = coverage_agent.process_message(req)
                requeried = False
                chunks    = result.get("retrieved_chunks", [])

                # --- step 2: show retrieved chunks state ---
                source_counts: Dict[str, int] = {}
                for c in chunks:
                    src = policy_name(c.get("source", "unknown"))
                    source_counts[src] = source_counts.get(src, 0) + 1
                src_line = ", ".join(f"**{s}** ({n})" for s, n in source_counts.items())
                _write_req_expander(ph, req_id, category, [
                    f"🔎 Querying retrieval system… ✓",
                    f"📄 Retrieved {len(chunks)} chunks from: {src_line}",
                    "🧠 Assessing coverage with Claude…",
                ], done=False)

                # --- re-query on low confidence ---
                if result.get("confidence") == "low" and result.get("suggested_recheck_terms"):
                    terms = result["suggested_recheck_terms"]
                    _write_req_expander(ph, req_id, category, [
                        "🔎 Querying retrieval system… ✓",
                        f"📄 Retrieved {len(chunks)} chunks from: {src_line}",
                        "🧠 Assessing coverage with Claude… ✓",
                        f"⚠️ Low confidence — triggering re-query with: "
                        + ", ".join(f"`{t}`" for t in terms),
                        "🔄 Re-querying…",
                    ], done=False)
                    recheck_msg = dict(req)
                    recheck_msg["recheck_terms"] = terms
                    try:
                        recheck = coverage_agent.process_message(recheck_msg)
                        _rank = {"Covered": 2, "Partial": 1, "At Risk": 0}
                        _conf = {"high": 2, "medium": 1, "low": 0}
                        if (_rank.get(recheck.get("assessment",""),0) + _conf.get(recheck.get("confidence",""),0) >=
                                _rank.get(result.get("assessment",""),0)  + _conf.get(result.get("confidence",""),0)):
                            result    = recheck
                            requeried = True
                    except Exception:
                        pass

            except Exception as e:
                result = {
                    "requirement_id":  req_id,
                    "assessment":      "At Risk",
                    "confidence":      "low",
                    "citations":       [],
                    "reasoning":       f"Analysis error: {type(e).__name__}: {e}",
                    "retrieved_chunks": [],
                }
                requeried = False

            result["_requeried"] = requeried

            # --- final state: collapse with full details ---
            assessment = result.get("assessment", "At Risk")
            confidence = result.get("confidence", "low")
            _write_req_expander(ph, req_id, category, [], done=True, result=result)

            bucket = {"Covered":"covered","Partial":"partial","At Risk":"at_risk"}.get(assessment,"at_risk")
            gap_report[bucket].append(req_id)
            gap_report["details"][req_id] = result
            steps.append({
                "req_id":     req_id,
                "category":   category,
                "assessment": assessment,
                "confidence": confidence,
                "reasoning":  result.get("reasoning", ""),
                "citations":  result.get("citations", []),
                "requeried":  requeried,
            })

        # ── Update init expander to "complete" ────────────────────────────────
        with init_ph.container():
            with st.expander("✅ **Orchestrator:** Analysis complete", expanded=False):
                st.markdown("Loading embeddings… ✓")
                st.markdown(f"Retrieval engine ready — **{len(retrieval._chunks)} chunks** indexed ✓")
                st.markdown("Initializing Coverage Agent… ✓")
                st.markdown(f"Parsed checklist — **{total} requirements** loaded ✓")
                st.markdown("---")
                st.markdown(
                    f"✅ **{len(gap_report['covered'])} covered** · "
                    f"⚠️ **{len(gap_report['partial'])} partial** · "
                    f"🚨 **{len(gap_report['at_risk'])} at risk**"
                )

    st.session_state["gap_report"]   = gap_report
    st.session_state["steps"]        = steps
    st.session_state["decision_log"] = orchestrator.get_message_log()

# ═══════════════════════════════════════════════════════════════════════════════
# GAP REPORT — rendered in TOP container from session state
# ═══════════════════════════════════════════════════════════════════════════════
if "gap_report" in st.session_state:
    report = st.session_state["gap_report"]
    details = report.get("details", {})
    total   = len(details)

    with report_area:
        st.markdown("---")
        st.markdown("## Gap Report")

        # Summary metrics
        n_cov  = len(report["covered"])
        n_par  = len(report["partial"])
        n_risk = len(report["at_risk"])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Analyzed",    total)
        c2.metric("✅ Covered",  n_cov)
        c3.metric("⚠️ Partial",  n_par)
        c4.metric("🚨 At Risk",  n_risk)
        c5.metric("Avg Confidence", avg_confidence(details))

        # Coverage bar
        if total:
            bar = "🟩" * n_cov + "🟨" * n_par + "🟥" * n_risk
            st.markdown(f"**Coverage:** {bar}")

        st.divider()

        tab_cov, tab_par, tab_risk = st.tabs([
            f"✅ Covered ({n_cov})",
            f"⚠️ Partial ({n_par})",
            f"🚨 At Risk ({n_risk})",
        ])

        with tab_cov:
            if not report["covered"]:
                st.info("No requirements fully covered.")
            for req_id in report["covered"]:
                d = report["details"][req_id]
                with st.expander(f"✅ {req_id} — {confidence_badge(d.get('confidence','?'))}"):
                    st.markdown(f"**Reasoning:** {d.get('reasoning','')}")
                    for i, c in enumerate(d.get("citations",[])[:2], 1):
                        render_citation(c, i)

        with tab_par:
            if not report["partial"]:
                st.info("No partially-covered requirements.")
            for req_id in report["partial"]:
                d = report["details"][req_id]
                with st.expander(f"⚠️ {req_id} — {confidence_badge(d.get('confidence','?'))}"):
                    st.markdown(f"**Reasoning:** {d.get('reasoning','')}")
                    for i, c in enumerate(d.get("citations",[])[:3], 1):
                        render_citation(c, i)
                    if d.get("suggested_recheck_terms"):
                        st.markdown("**Recheck terms:** " +
                                    "  ".join(f"`{t}`" for t in d["suggested_recheck_terms"]))

        with tab_risk:
            if not report["at_risk"]:
                st.success("No at-risk requirements!")
            for req_id in report["at_risk"]:
                d = report["details"][req_id]
                with st.expander(f"🚨 {req_id} — {confidence_badge(d.get('confidence','?'))}"):
                    st.markdown(f"**Reasoning:** {d.get('reasoning','')}")
                    st.markdown("**Suggested next steps:**")
                    st.markdown(
                        "- Draft or locate a policy that addresses this requirement\n"
                        "- Engage the control owner to document evidence\n"
                        "- Add to remediation backlog with target date"
                    )
                    for i, c in enumerate(d.get("citations",[])[:2], 1):
                        render_citation(c, i)

        # Export
        st.divider()
        export = {"gap_report": report, "decision_log": st.session_state.get("decision_log", [])}
        st.download_button(
            "⬇️ Download Decision Log (JSON)",
            data=json.dumps(export, indent=2),
            file_name="auditprep_decision_log.json",
            mime="application/json",
        )

        # ── Email drafting prompt ─────────────────────────────────────────────
        st.divider()
        st.markdown("#### 📧 Draft emails for at-risk items?")
        at_risk_ids = report.get("at_risk", [])
        if at_risk_ids:
            st.caption(
                f"I found {len(at_risk_ids)} at-risk requirements: "
                f"{', '.join(at_risk_ids)}. "
                "Would you like me to draft remediation emails to control owners?"
            )
        else:
            st.caption("No at-risk items — nothing to email!")

        _e1, _e2, _e3, _e4 = st.columns([1, 1, 1, 3])
        if _e1.button("✅ Yes", key="email_yes"):
            st.info("📬 **v2 coming soon** — email drafting will be available in the next release.")
        if _e2.button("❌ No", key="email_no"):
            st.success("Got it! Analysis complete.")

# ── footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='footer'>Built with <strong>Claude Sonnet 4</strong> &nbsp;|&nbsp; "
    "Powered by <strong>OpenAI Embeddings</strong> &nbsp;|&nbsp; "
    "<a href='https://github.com/lalithapammi/audit-prep-agent' style='color:#aaa;'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
