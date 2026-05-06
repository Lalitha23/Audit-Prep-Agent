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
CHECKLIST_CSV   = _BASE / "data" / "synthetic" / "checklists" / "soc2_sample.csv"
EMBEDDINGS_JSON = _BASE / "data" / "embeddings" / "policy_embeddings.json"

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
    scores = [CONFIDENCE_SCORES.get(d.get("confidence", "low"), 0) for d in details.values()]
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

def _src_summary(chunks: List[Dict]) -> str:
    sc: Dict[str, int] = {}
    for c in chunks:
        s = policy_name(c.get("source", "unknown"))
        sc[s] = sc.get(s, 0) + 1
    return ", ".join(f"{s} ({n})" for s, n in sc.items()) or "none"


def _write_req_expander(ph, req_id: str, category: str, lines: List[str],
                        done: bool = False, result: Optional[Dict] = None) -> None:
    """Write/update a single requirement's detail expander into placeholder *ph*.

    During processing (done=False): expander is expanded with live step lines.
    After completion (done=True):   collapses and shows full detail.
      - If result contains '_first_attempt', renders the three-phase
        self-correction view (first attempt → orchestrator trigger → second attempt).
      - Otherwise renders a plain single-pass view.
    """
    assessment = (result or {}).get("assessment", "")
    confidence = (result or {}).get("confidence", "")
    requeried  = (result or {}).get("_requeried", False)

    if done and assessment:
        icon  = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(assessment, "❓")
        title = (f"{icon} **{req_id}** — {assessment} "
                 f"({confidence_badge(confidence)})"
                 + (" ↩️" if requeried else ""))
    else:
        title = f"⏳ **{req_id}** — analyzing…"

    with ph.container():
        with st.expander(title, expanded=not done):
            st.caption(category)
            for line in lines:
                st.markdown(line)

            if not done:
                return

            first_att = (result or {}).get("_first_attempt")

            if first_att:
                # ── THREE-PHASE SELF-CORRECTION VIEW ─────────────────────────
                _conf_rank = {"high": 2, "medium": 1, "low": 0}

                # — First attempt ——————————————————————————————————————————————
                fa_assess = first_att.get("assessment", "")
                fa_conf   = first_att.get("confidence", "")
                fa_reason = first_att.get("reasoning", "")
                fa_icon   = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(fa_assess, "❓")
                fa_chunks = first_att.get("retrieved_chunks", [])

                st.markdown("##### 🔍 First Attempt")
                st.caption(f"📄 {len(fa_chunks)} chunks retrieved — {_src_summary(fa_chunks)}")
                st.markdown(
                    f"**Assessment:** {fa_icon} {fa_assess} &nbsp;|&nbsp; "
                    f"**Confidence:** {confidence_badge(fa_conf)}"
                )
                if fa_reason:
                    st.info(f"💬 {fa_reason}")

                # — Orchestrator self-correction trigger ————————————————————————
                recheck_terms = (result or {}).get("_recheck_terms", [])
                trigger_reason = (
                    "Low confidence detected"
                    if fa_conf == "low"
                    else "Partial coverage — re-querying for stronger evidence"
                )
                st.markdown("---")
                st.warning(
                    f"⚠️ **Orchestrator:** {trigger_reason} — triggering re-query\n\n"
                    + "🔑 **Refined search terms:** "
                    + " &nbsp;".join(f"`{t}`" for t in recheck_terms)
                )

                # — Second attempt ——————————————————————————————————————————————
                sa_assess = (result or {}).get("assessment", "")
                sa_conf   = (result or {}).get("confidence", "")
                sa_reason = (result or {}).get("reasoning", "")
                sa_icon   = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(sa_assess, "❓")
                sa_chunks = (result or {}).get("retrieved_chunks", [])
                accepted  = (result or {}).get("_recheck_accepted", True)

                st.markdown("---")
                st.markdown("##### 🔄 Second Attempt (refined terms)")
                st.caption(f"📄 {len(sa_chunks)} chunks retrieved — {_src_summary(sa_chunks)}")
                st.markdown(
                    f"**Assessment:** {sa_icon} {sa_assess} &nbsp;|&nbsp; "
                    f"**Confidence:** {confidence_badge(sa_conf)}"
                )
                if sa_reason:
                    st.info(f"💬 {sa_reason}")

                if accepted and _conf_rank.get(sa_conf, 0) > _conf_rank.get(fa_conf, 0):
                    st.success("✅ Confidence improved — accepting re-query result")
                elif accepted:
                    st.success("✅ Re-query result accepted (equal or better score)")
                else:
                    st.warning("↩️ Original result kept — re-query did not improve")

            else:
                # ── SINGLE-PASS VIEW ──────────────────────────────────────────
                chunks    = (result or {}).get("retrieved_chunks", [])
                citations = (result or {}).get("citations", [])
                reasoning = (result or {}).get("reasoning", "")

                # Explicit assessment + confidence summary
                a_icon = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(assessment, "❓")
                st.markdown(
                    f"**Assessment:** {a_icon} {assessment} &nbsp;|&nbsp; "
                    f"**Confidence:** {confidence_badge(confidence)}"
                )

                if chunks:
                    st.markdown("---")
                    st.markdown("**🔎 Retrieved evidence chunks:**")
                    st.caption(f"Sources: {_src_summary(chunks)}")
                    top       = chunks[0]
                    top_text  = top.get("text", "")[:200].replace("\n", " ")
                    top_score = top.get("score", 0.0)
                    st.info(f'**Top chunk** (relevance {top_score:.3f}):\n\n"{top_text}…"')

                if citations:
                    st.markdown("**📄 Citations from Claude:**")
                    for i, c in enumerate(citations[:3], 1):
                        render_citation(c, i)

                if reasoning:
                    st.markdown(f"**🧠 Reasoning:**\n\n{reasoning}")


def _render_gap_report(gap_report: Dict) -> None:
    """Render the gap report section (metrics + tabs for each bucket)."""
    details = gap_report.get("details", {})
    total   = len(details)
    n_cov   = len(gap_report["covered"])
    n_par   = len(gap_report["partial"])
    n_risk  = len(gap_report["at_risk"])

    st.markdown("---")
    st.markdown("### 📊 Gap Report")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Analyzed",         total)
    c2.metric("✅ Covered",       n_cov)
    c3.metric("⚠️ Partial",       n_par)
    c4.metric("🚨 At Risk",       n_risk)
    c5.metric("Avg Confidence",   avg_confidence(details))

    if total:
        bar = "🟩" * n_cov + "🟨" * n_par + "🟥" * n_risk
        st.markdown(f"**Coverage:** {bar}")

    # Three clickable sections — use tabs (nested expanders unsupported by Streamlit)
    tab_cov, tab_par, tab_risk = st.tabs([
        f"✅ Covered ({n_cov})",
        f"⚠️ Partial ({n_par})",
        f"🚨 At Risk ({n_risk})",
    ])

    with tab_cov:
        if not gap_report["covered"]:
            st.info("No requirements fully covered.")
        for req_id in gap_report["covered"]:
            d = details[req_id]
            with st.expander(f"✅ {req_id} — {confidence_badge(d.get('confidence', '?'))}"):
                st.markdown(f"**Reasoning:** {d.get('reasoning', '')}")
                for i, c in enumerate(d.get("citations", [])[:2], 1):
                    render_citation(c, i)

    with tab_par:
        if not gap_report["partial"]:
            st.info("No partially-covered requirements.")
        for req_id in gap_report["partial"]:
            d = details[req_id]
            with st.expander(f"⚠️ {req_id} — {confidence_badge(d.get('confidence', '?'))}"):
                st.markdown(f"**Reasoning:** {d.get('reasoning', '')}")
                for i, c in enumerate(d.get("citations", [])[:3], 1):
                    render_citation(c, i)
                if d.get("suggested_recheck_terms"):
                    st.markdown("**Recheck terms:** " +
                                "  ".join(f"`{t}`" for t in d["suggested_recheck_terms"]))

    with tab_risk:
        if not gap_report["at_risk"]:
            st.success("No at-risk requirements!")
        for req_id in gap_report["at_risk"]:
            d = details[req_id]
            with st.expander(f"🚨 {req_id} — {confidence_badge(d.get('confidence', '?'))}"):
                st.markdown(f"**Reasoning:** {d.get('reasoning', '')}")
                st.markdown("**Suggested next steps:**")
                st.markdown(
                    "- Draft or locate a policy that addresses this requirement\n"
                    "- Engage the control owner to document evidence\n"
                    "- Add to remediation backlog with target date"
                )
                for i, c in enumerate(d.get("citations", [])[:2], 1):
                    render_citation(c, i)

    st.divider()
    export = {
        "gap_report":   gap_report,
        "decision_log": st.session_state.get("decision_log", []),
    }
    st.download_button(
        "⬇️ Download Decision Log (JSON)",
        data=json.dumps(export, indent=2),
        file_name="auditprep_decision_log.json",
        mime="application/json",
    )


def _render_email_prompt(gap_report: Dict) -> None:
    """Render follow-up text about email notifications."""
    at_risk = gap_report.get("at_risk", [])
    st.markdown("---")
    if at_risk:
        st.info(
            f"Would you like me to draft email notifications for the "
            f"**{len(at_risk)} at-risk** requirement(s)? "
            f"({', '.join(at_risk)}) — *Email Agent coming in v2*"
        )
    else:
        st.info("✅ All requirements have coverage — no remediation emails needed.")


def _render_completed_progress(steps: List[Dict], gap_report: Dict,
                                retrieval: InMemoryRetrieval) -> None:
    """Reconstruct completed progress log from stored session state."""
    total = len(steps)

    st.markdown("#### 🤖 Agent Activity")

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

    for step in steps:
        req_id = step["req_id"]
        result = dict(gap_report["details"].get(req_id, {}))
        result["_requeried"] = step.get("requeried", False)
        ph = st.empty()
        _write_req_expander(ph, req_id, step["category"], [], done=True, result=result)

    _render_gap_report(gap_report)
    _render_email_prompt(gap_report)


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
# 1. ALWAYS-VISIBLE INFO BOX
# ═══════════════════════════════════════════════════════════════════════════════
st.info(
    "💡 This multi-agent system analyzes your policy documents against SOC 2 requirements "
    "using semantic search and AI reasoning to identify coverage gaps."
)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. USER MESSAGE + BUTTON — cleared immediately when analysis starts
# ═══════════════════════════════════════════════════════════════════════════════
# Wrap in st.empty() so we can call input_ph.empty() to wipe it the instant
# the button is clicked, before any analysis output appears.
input_ph = st.empty()

if "gap_report" not in st.session_state:
    with input_ph.container():
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

        _bcol1, _bcol2, _bcol3 = st.columns([1, 2, 1])
        with _bcol2:
            run_btn = st.button(
                "▶ Start Analysis",
                type="primary",
                use_container_width=True,
                disabled=bool(_missing),
                key="run_btn",
            )
else:
    run_btn = False

# ═══════════════════════════════════════════════════════════════════════════════
# 3. PROGRESS + REPORT AREA
# ═══════════════════════════════════════════════════════════════════════════════
progress_area = st.container()

# ── LIVE ANALYSIS RUN ────────────────────────────────────────────────────────
if run_btn:
    input_ph.empty()   # wipe user message + button immediately

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

        # ── Per-requirement placeholders ──────────────────────────────────────
        req_placeholders = {req["requirement_id"]: st.empty() for req in requirements}

        # ── Process each requirement ──────────────────────────────────────────
        for idx, req in enumerate(requirements, 1):
            req_id   = req["requirement_id"]
            category = req["category"]
            ph       = req_placeholders[req_id]

            # ── Phase 1: first attempt ─────────────────────────────────────
            _write_req_expander(ph, req_id, category, [
                "🔍 **First attempt:** querying retrieval system…",
            ], done=False)

            try:
                first_result = coverage_agent.process_message(req)
                requeried    = False
                fa_chunks    = first_result.get("retrieved_chunks", [])
                fa_assess    = first_result.get("assessment", "At Risk")
                fa_conf      = first_result.get("confidence", "low")
                fa_reason    = first_result.get("reasoning", "")
                fa_icon      = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(fa_assess, "❓")

                # Show first-attempt result
                _write_req_expander(ph, req_id, category, [
                    "🔍 **First attempt:** querying retrieval system… ✓",
                    f"   📄 Retrieved {len(fa_chunks)} chunks — {_src_summary(fa_chunks)}",
                    f"   {fa_icon} Assessment: **{fa_assess}** | Confidence: {confidence_badge(fa_conf)}",
                    f"   💬 _{fa_reason[:130]}…_",
                ], done=False)

                # ── Phase 2: decide whether to re-query ───────────────────────
                terms          = first_result.get("suggested_recheck_terms", [])
                should_requery = bool(terms) and fa_conf == "low"

                if should_requery:
                    trigger_reason = (
                        "Low confidence detected"
                        if fa_conf == "low"
                        else "Partial coverage — re-querying for stronger evidence"
                    )
                    _write_req_expander(ph, req_id, category, [
                        "🔍 **First attempt:** querying retrieval system… ✓",
                        f"   📄 Retrieved {len(fa_chunks)} chunks — {_src_summary(fa_chunks)}",
                        f"   {fa_icon} Assessment: **{fa_assess}** | Confidence: {confidence_badge(fa_conf)}",
                        f"   💬 _{fa_reason[:130]}…_",
                        "",
                        f"⚠️ **Orchestrator:** {trigger_reason} — triggering re-query",
                        "   🔑 Refined terms: " + " ".join(f"`{t}`" for t in terms),
                        "",
                        "🔄 **Second attempt:** re-analyzing with refined terms…",
                    ], done=False)

                    recheck_msg = dict(req)
                    recheck_msg["recheck_terms"] = terms
                    recheck_result = coverage_agent.process_message(recheck_msg)

                    _rank = {"Covered": 2, "Partial": 1, "At Risk": 0}
                    _conf = {"high": 2, "medium": 1, "low": 0}
                    score1 = _rank.get(fa_assess, 0) + _conf.get(fa_conf, 0)
                    score2 = (_rank.get(recheck_result.get("assessment", ""), 0) +
                              _conf.get(recheck_result.get("confidence", ""), 0))
                    accepted_recheck = score2 >= score1

                    result    = recheck_result if accepted_recheck else first_result
                    requeried = True

                    result["_first_attempt"]    = first_result
                    result["_recheck_terms"]    = terms
                    result["_recheck_accepted"] = accepted_recheck
                else:
                    result = first_result

            except Exception as e:
                result = {
                    "requirement_id":   req_id,
                    "assessment":       "At Risk",
                    "confidence":       "low",
                    "citations":        [],
                    "reasoning":        f"Analysis error: {type(e).__name__}: {e}",
                    "retrieved_chunks": [],
                }
                requeried = False

            result["_requeried"] = requeried

            # final: collapse with full details
            assessment = result.get("assessment", "At Risk")
            confidence = result.get("confidence", "low")
            _write_req_expander(ph, req_id, category, [], done=True, result=result)

            bucket = {"Covered": "covered", "Partial": "partial", "At Risk": "at_risk"}.get(
                assessment, "at_risk"
            )
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

        # ── Update init expander to completed ────────────────────────────────
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

        # ── Gap report (inline, below progress) ──────────────────────────────
        _render_gap_report(gap_report)
        _render_email_prompt(gap_report)

    st.session_state["gap_report"]   = gap_report
    st.session_state["steps"]        = steps
    st.session_state["decision_log"] = orchestrator.get_message_log()

# ── RECONSTRUCT FROM SESSION STATE (rerenders after analysis) ────────────────
elif "gap_report" in st.session_state:
    with progress_area:
        _render_completed_progress(
            steps      = st.session_state["steps"],
            gap_report = st.session_state["gap_report"],
            retrieval  = get_retrieval_engine(),
        )

# ── footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='footer'>Built with <strong>Claude Sonnet 4</strong> &nbsp;|&nbsp; "
    "Powered by <strong>OpenAI Embeddings</strong> &nbsp;|&nbsp; "
    "<a href='https://github.com/lalithapammi/audit-prep-agent' style='color:#aaa;'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
