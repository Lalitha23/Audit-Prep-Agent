import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

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

POLICY_NAMES = {
    "access_control_policy.pdf":        "Access Control Policy",
    "information_security_policy.pdf":  "Information Security Policy",
    "vendor_management_policy.pdf":     "Vendor Management Policy",
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

    with st.expander("⚙️ How It Works"):
        st.markdown(
            """
**Multi-Agent Architecture**

1. **Orchestrator Agent**
   Receives the full SOC 2 checklist and coordinates the analysis loop.
   For each requirement, it delegates to the Coverage Agent and handles
   low-confidence re-queries automatically.

2. **Coverage Agent**
   For each requirement it:
   - Queries the retrieval engine with the requirement text
   - Receives the top-5 most semantically similar policy chunks
   - Sends requirement + evidence to Claude Sonnet for assessment
   - Returns a structured verdict: Covered / Partial / At Risk

3. **Semantic Search (Retrieval)**
   Policy documents are pre-chunked (~375 words), embedded with
   `text-embedding-3-small`, and stored in memory. At query time,
   the requirement text is embedded and ranked by cosine similarity
   against all policy chunks — no keyword matching required.

4. **Re-query Logic**
   If Claude returns low confidence, the Orchestrator triggers one
   additional retrieval pass using Claude's own suggested recheck terms,
   then keeps whichever result scores higher.
            """
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


@st.cache_resource(show_spinner="Loading retrieval engine...")
def get_retrieval_engine() -> InMemoryRetrieval:
    if not EMBEDDINGS_JSON.exists():
        raise FileNotFoundError(
            f"Embeddings file not found at {EMBEDDINGS_JSON}. "
            "Run `python3 scripts/generate_embeddings.py` first."
        )
    try:
        return InMemoryRetrieval(embeddings_path=EMBEDDINGS_JSON)
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Embeddings file is corrupted or has unexpected format: {e}")


def confidence_badge(level: str) -> str:
    return {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}.get(level, f"❓ {level}")


def policy_display_name(filename: str) -> str:
    return POLICY_NAMES.get(filename, filename)


def render_citation(c: Dict, idx: int) -> None:
    source  = c.get("source", "unknown")
    excerpt = c.get("excerpt", "").strip()[:300]
    score   = c.get("score", 0.0)
    label   = policy_display_name(source)
    score_pct = int(score * 100)
    score_bar = "█" * (score_pct // 10) + "░" * (10 - score_pct // 10)

    with st.expander(f"📄 Citation {idx} — {label}  |  relevance: {score:.3f}"):
        col_score, col_src = st.columns([1, 3])
        col_score.metric("Relevance", f"{score:.3f}")
        col_src.markdown(f"**Source:** `{source}`")
        if excerpt:
            st.markdown("**Relevant excerpt:**")
            st.info(f'"{excerpt}"')
        else:
            st.caption("No excerpt available.")


def avg_confidence(details: Dict) -> float:
    scores = [CONFIDENCE_SCORES.get(d.get("confidence", "low"), 0.0)
              for d in details.values()]
    return sum(scores) / len(scores) if scores else 0.0


def render_summary_stats(report: Dict) -> None:
    details = report.get("details", {})
    total   = len(details)
    n_cov   = len(report["covered"])
    n_par   = len(report["partial"])
    n_risk  = len(report["at_risk"])
    avg_conf = avg_confidence(details)
    conf_label = (
        "🟢 High" if avg_conf >= 0.75 else
        "🟡 Medium" if avg_conf >= 0.35 else
        "🔴 Low"
    )

    st.markdown("### Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Analyzed", total)
    c2.metric("✅ Covered",  n_cov,  delta=None)
    c3.metric("⚠️ Partial",  n_par,  delta=None)
    c4.metric("🚨 At Risk",  n_risk, delta=None)
    c5.metric("Avg Confidence", conf_label)

    # coverage bar
    if total:
        cov_pct  = n_cov  / total
        par_pct  = n_par  / total
        risk_pct = n_risk / total
        st.markdown(
            f"**Coverage breakdown:** "
            f"{'█' * round(cov_pct  * 20)}{'░' * round(par_pct  * 20)}"
            f"{'·' * round(risk_pct * 20)}  "
            f"({n_cov} covered / {n_par} partial / {n_risk} at risk out of {total})"
        )


# ── main page ─────────────────────────────────────────────────────────────────
st.title("🔍 AuditPrep Agent")
st.subheader("Multi-Agent SOC 2 Audit Gap Analysis")

# ── pre-flight key check (non-blocking warning) ───────────────────────────────
_missing_keys = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if _missing_keys:
    st.warning(
        f"**Missing API key(s):** {', '.join(_missing_keys)}  \n"
        "Add them to your `.env` file before running analysis. "
        "See `.env.example` for the required format.",
        icon="⚠️",
    )

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

run_btn = st.button(
    "▶ Run Analysis",
    type="primary",
    use_container_width=True,
    disabled=bool(_missing_keys),
)

if run_btn:
    # ── hard stop if keys still missing ──────────────────────────────────────
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        st.error(
            f"Cannot run analysis — missing: {', '.join(missing)}.  \n"
            "Add the key(s) to your `.env` file and reload the page."
        )
        st.stop()

    # ── load checklist ────────────────────────────────────────────────────────
    try:
        requirements = load_requirements()
    except FileNotFoundError as e:
        st.error(f"**Checklist not found:** {e}")
        st.stop()
    except Exception as e:
        st.error(f"**Could not load checklist:** {e}")
        st.stop()

    total = len(requirements)

    # ── initialise agents ─────────────────────────────────────────────────────
    try:
        retrieval      = get_retrieval_engine()
        coverage_agent = CoverageAgent(retrieval_engine=retrieval)
        orchestrator   = OrchestratorAgent(coverage_agent=coverage_agent)
    except FileNotFoundError as e:
        st.error(f"**Embeddings file missing:** {e}")
        st.stop()
    except ValueError as e:
        st.error(f"**Corrupted embeddings file:** {e}  \nDelete and re-run `generate_embeddings.py`.")
        st.stop()
    except EnvironmentError as e:
        st.error(f"**API key error:** {e}")
        st.stop()
    except Exception as e:
        st.error(f"**Initialisation error:** {e}")
        st.stop()

    # ── run analysis with live progress ───────────────────────────────────────
    st.markdown("### Processing Requirements")
    progress_bar = st.progress(0)
    status_text  = st.empty()
    results_area = st.container()

    gap_report: Dict = {"covered": [], "partial": [], "at_risk": [], "details": {}}

    for idx, req in enumerate(requirements):
        req_id = req["requirement_id"]
        status_text.markdown(
            f"**Processing requirement {idx + 1}/{total}: `{req_id}`** — {req['category']}"
        )
        progress_bar.progress(idx / total)

        try:
            result = coverage_agent.process_message(req)

            # one re-query on low confidence
            if result.get("confidence") == "low" and result.get("suggested_recheck_terms"):
                recheck_msg = dict(req)
                recheck_msg["recheck_terms"] = result["suggested_recheck_terms"]
                try:
                    recheck = coverage_agent.process_message(recheck_msg)
                    _rank = {"Covered": 2, "Partial": 1, "At Risk": 0}
                    _conf = {"high": 2, "medium": 1, "low": 0}
                    if (
                        _rank.get(recheck.get("assessment", ""), 0)
                        + _conf.get(recheck.get("confidence", ""), 0)
                        >= _rank.get(result.get("assessment", ""), 0)
                        + _conf.get(result.get("confidence", ""), 0)
                    ):
                        result = recheck
                except Exception:
                    pass  # keep original result if recheck fails

        except Exception as e:
            result = {
                "requirement_id": req_id,
                "assessment":     "At Risk",
                "confidence":     "low",
                "citations":      [],
                "reasoning":      f"Analysis failed — {type(e).__name__}: {e}. Manual review required.",
            }

        assessment = result.get("assessment", "At Risk")
        bucket = {"Covered": "covered", "Partial": "partial", "At Risk": "at_risk"}.get(
            assessment, "at_risk"
        )
        gap_report[bucket].append(req_id)
        gap_report["details"][req_id] = result

        icon = {"Covered": "✅", "Partial": "⚠️", "At Risk": "🚨"}.get(assessment, "❓")
        with results_area:
            st.markdown(
                f"{icon} **{req_id}** — {assessment} "
                f"({confidence_badge(result.get('confidence', '?'))})"
            )

    progress_bar.progress(1.0)
    status_text.markdown("**Analysis complete.**")
    st.success(
        f"Processed {total} requirements — "
        f"✅ {len(gap_report['covered'])} covered · "
        f"⚠️ {len(gap_report['partial'])} partial · "
        f"🚨 {len(gap_report['at_risk'])} at risk"
    )

    st.session_state["gap_report"]   = gap_report
    st.session_state["orchestrator"] = orchestrator
    st.session_state["log"]          = orchestrator.get_message_log()


# ── gap report ────────────────────────────────────────────────────────────────
if "gap_report" in st.session_state:
    report = st.session_state["gap_report"]

    st.divider()
    st.markdown("## Gap Report")

    # ── summary stats ─────────────────────────────────────────────────────────
    render_summary_stats(report)
    st.divider()

    tab_covered, tab_partial, tab_risk = st.tabs([
        f"✅ Covered ({len(report['covered'])})",
        f"⚠️ Partial ({len(report['partial'])})",
        f"🚨 At Risk ({len(report['at_risk'])})",
    ])

    with tab_covered:
        if not report["covered"]:
            st.info("No requirements are fully covered by the current policy set.")
        for req_id in report["covered"]:
            d = report["details"][req_id]
            with st.expander(
                f"✅ {req_id} — {d.get('assessment')} ({confidence_badge(d.get('confidence','?'))})"
            ):
                st.markdown(f"**Reasoning:** {d.get('reasoning', '')}")
                citations = d.get("citations", [])
                if citations:
                    st.markdown("**Supporting citations:**")
                    for i, c in enumerate(citations[:2], 1):
                        render_citation(c, i)

    with tab_partial:
        if not report["partial"]:
            st.info("No partially-covered requirements.")
        for req_id in report["partial"]:
            d = report["details"][req_id]
            with st.expander(
                f"⚠️ {req_id} — {d.get('assessment')} ({confidence_badge(d.get('confidence','?'))})"
            ):
                st.markdown(f"**Reasoning:** {d.get('reasoning', '')}")
                citations = d.get("citations", [])
                if citations:
                    st.markdown("**Supporting citations:**")
                    for i, c in enumerate(citations[:3], 1):
                        render_citation(c, i)
                recheck = d.get("suggested_recheck_terms")
                if recheck:
                    st.markdown(
                        f"**Suggested recheck terms:** "
                        + "  ".join(f"`{t}`" for t in recheck)
                    )

    with tab_risk:
        if not report["at_risk"]:
            st.success("No at-risk requirements — great coverage!")
        for req_id in report["at_risk"]:
            d = report["details"][req_id]
            with st.expander(
                f"🚨 {req_id} — {d.get('assessment')} ({confidence_badge(d.get('confidence','?'))})"
            ):
                st.markdown(f"**Reasoning:** {d.get('reasoning', '')}")
                st.markdown("**Suggested next steps:**")
                st.markdown(
                    "- Draft or locate an existing policy that addresses this requirement\n"
                    "- Engage the relevant control owner to document evidence\n"
                    "- Add to remediation backlog with a target completion date\n"
                    "- Consider a gap assessment workshop with the policy owner"
                )
                citations = d.get("citations", [])
                if citations:
                    st.markdown("**Partial evidence found:**")
                    for i, c in enumerate(citations[:2], 1):
                        render_citation(c, i)
                recheck = d.get("suggested_recheck_terms")
                if recheck:
                    st.markdown(
                        f"**Suggested recheck terms:** "
                        + "  ".join(f"`{t}`" for t in recheck)
                    )

    # ── export ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Export")

    export_payload = {
        "gap_report":   report,
        "decision_log": st.session_state.get("log", []),
    }

    st.download_button(
        label="⬇️ Download Decision Log (JSON)",
        data=json.dumps(export_payload, indent=2),
        file_name="auditprep_decision_log.json",
        mime="application/json",
        use_container_width=True,
    )

# ── footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85em;'>"
    "Built with <strong>Claude Sonnet 4</strong> &nbsp;|&nbsp; "
    "Powered by <strong>OpenAI Embeddings</strong> &nbsp;|&nbsp; "
    "<a href='https://github.com/lalithapammi/audit-prep-agent' style='color:#888;'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
