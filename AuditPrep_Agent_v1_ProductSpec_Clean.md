# AuditPrep Agent — v1 Product Specification

---

## 🎯 Origin Story

In enterprise government compliance SaaS, audit prep is a coordination problem disguised as a documentation problem. I saw this firsthand at Maximus, where I owned the Provider Data Management System (PDMS) — the platform that processed Medicaid and Medicare provider enrollments for state agencies. Our environment was audited by major firms on combined SOC 1 and SOC 2 scopes, depending on the contract.

The same audit vendor audits multiple service providers — Maximus, Conduent, and others — against overlapping but distinct compliance frameworks. Every audit cycle, compliance teams across these companies do nearly identical work: parse the auditor's checklist, hunt down policy evidence across SharePoint, Jira and email, chase cross-functional teams for missing documentation, and assemble the response package.

The hard part isn't the analysis. It's the coordination: tracking down evidence scattered across teams, surfacing gaps before the auditor does, and routing asks to the right owners.

This project is my attempt to redesign that workflow with a multi-agent system — an orchestrator that plans the work, a coverage specialist that analyzes evidence, and a roadmap toward outreach agents that handle cross-functional asks.

---

## 🚨 Problem Statement

Audit preparation suffers from:

**Fragmented evidence**
- Policies, controls, and evidence live in disconnected systems (SharePoint, PDFs, tickets)

**Late discovery of gaps**
- Missing evidence is identified during audit response, not before

**No institutional memory**
- Prior audit findings are not reused effectively

**Manual coordination overhead**
- Compliance teams spend time chasing people, not analyzing compliance

**Semantic mismatch**
- Audit language ≠ internal policy language (keyword search fails)

---

## 👤 Target User

**Primary:** Compliance Lead / Compliance Manager

**Context:**
- Works in SOC 2 / SOC 1 / regulated SaaS environments
- Manages cross-functional stakeholders (security, engineering, HR)
- Uses SharePoint, spreadsheets, email for audit prep
- Has used GRC tools but finds them rigid or expensive
- Comfortable with AI tools but skeptical of black-box automation in regulated environments

---

## 💡 Product Vision

A multi-agent audit coordination system that:
- Understands audit requirements semantically
- Retrieves relevant policy evidence automatically
- Identifies coverage gaps early in the cycle
- Maintains a traceable decision trail
- Evolves into organizational compliance memory over time

**Long-term:** The system becomes institutional memory across audit cycles — it knows what was flagged last year, who owned remediation, what evidence satisfied the auditor, and what's at risk this cycle.

---

## ⚙️ Core Value Proposition

AuditPrep Agent transforms audit preparation from manual coordination into an **agent-driven workflow** that retrieves, evaluates, and flags compliance coverage with **traceable reasoning**.

Unlike spreadsheets and generic GRC platforms that leave coordination work to humans, our system delegates analysis to specialized agents while keeping humans in control of high-stakes decisions.

---

## 🧪 v1 Scope

### Core Objective

Prove that **multi-agent coordination + retrieval-based reasoning** can automate audit gap analysis end-to-end.

### What's Included

- **Two agents:** Orchestrator + Coverage Agent
- **One document type:** Internal policies (PDF)
- **One audit framework:** SOC 2 Type II Trust Services Criteria (12 sample requirements)
- **Retrieval system:** Semantic search with abstraction layer (enables future upgrades)
- **Self-correction:** Confidence-based re-query loop (max 1 retry per requirement)
- **Memory:** Decision log capturing all agent decisions
- **Output:** Gap report with 3 categories (Covered / Partial / At Risk)
- **UI:** Streamlit web interface (upload → processing → report)
- **Deployment:** Streamlit Cloud (public demo)
- **Data:** Synthetic dataset only (SOC 2 checklist + 3 policies with seeded gaps)

### What's Explicitly Out of Scope

**Not Included in v1:**
- ❌ SharePoint integration → Deferred to v1.5 (MCP-based; synthetic data sufficient to prove v1 hypothesis)
- ❌ Real customer data → Privacy/legal risk; synthetic data proves concept
- ❌ Custom file upload → Increases scope; demo dataset sufficient for validation
- ❌ Cloud vector database (Pinecone) → In-memory retrieval adequate for v1 scale
- ❌ Multi-tenancy → Single demo instance sufficient for validation
- ❌ Live agent conversation UI → Simplified to progress spinner

**Rationale:** Maintain focused scope on proving multi-agent orchestration pattern. Each removed feature either adds infrastructure complexity or operational risk without validating core hypothesis.

---

## 🏗️ System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                    (Streamlit Web App)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Orchestrator Agent   │
              │                      │
              │ • Parses checklist   │
              │ • Delegates tasks    │
              │ • Evaluates results  │
              │ • Triggers re-query  │
              │ • Generates report   │
              └──────┬───────────────┘
                     │
                     │ (Sends requirements)
                     ▼
              ┌──────────────────────┐
              │  Coverage Agent      │
              │                      │
              │ • Retrieves evidence │
              │ • Assesses coverage  │
              │ • Returns citations  │
              └──────┬───────────────┘
                     │
                     │ (Queries for evidence)
                     ▼
              ┌──────────────────────┐
              │  Retrieval Engine    │
              │  (Abstraction Layer) │
              │                      │
              │  Semantic Search     │
              └──────┬───────────────┘
                     │
                     ▼
              ┌──────────────────────┐
              │   Policy Store       │
              │                      │
              │ • Pre-indexed docs   │
              │ • Entity metadata    │
              └──────────────────────┘
```

### Component Responsibilities

**User Interface**
- File upload (audit checklist + policy PDFs)
- Progress visualization
- Gap report display with coverage classifications

**Orchestrator Agent**
- Parses SOC 2 checklist into individual requirements
- Delegates each requirement to Coverage Agent
- Evaluates confidence scores in responses
- Triggers bounded re-query loop (max 1 retry) on low confidence
- Maintains decision log (audit trail of all decisions)
- Generates final gap report

**Coverage Agent**
- Receives requirement from Orchestrator
- Queries Retrieval Engine for relevant policy chunks
- Analyzes semantic coverage against requirement
- Returns structured assessment with citations and confidence score
- Suggests alternative search terms if confidence is low

**Retrieval Engine (Abstraction Layer)**
- Semantic search over policy documents
- v1 implementation: In-memory vector search
- Designed to support future upgrades (FAISS, Pinecone, graph-hybrid) without agent code changes

**Policy Store**
- Pre-processed policy documents with semantic embeddings
- Entity metadata: controls addressed, framework, evidence type
- Enables future graph-based enhancements without data reprocessing

### Key Architectural Decisions

**Multi-Agent Separation**
- Orchestrator and Coverage Agent have distinct tool access
- Prevents agent collapse into single-agent wrapper
- Enforced at code level, not just prompts

**Retrieval Abstraction**
- Interface decouples agents from storage implementation
- v1 → v2 upgrade requires zero agent code changes
- Supports future graph-hybrid retrieval

**Self-Correction Loop**
- Confidence-based re-query mechanism
- Hard cap: 1 retry per requirement (prevents infinite loops)
- "Needs Human Review" flag for persistent low confidence

**Decision Auditability**
- All Orchestrator decisions logged with timestamp, reasoning, confidence
- Enables debugging and process improvement
- Decision log exportable for review

---

## 🎯 Primary Use Case

**Actor:** Compliance Manager preparing for SOC 2 audit

**Preconditions:**
- User has SOC 2 audit checklist (12 requirements)
- User has internal policy documents (3 PDFs)

**Main Flow:**
1. User navigates to demo URL
2. System displays interface with demo dataset pre-selected
3. User clicks "Run Analysis"
4. System processes requirements and displays progress
5. System generates gap report with three classifications:
   - Covered (5 requirements)
   - Partial (4 requirements)
   - At Risk (3 requirements)
6. User reviews coverage details, citations, and reasoning for each requirement
7. User downloads decision log (JSON) for audit trail

**Success Criteria:**
- User completes workflow without errors
- Gap report matches expected ground truth
- User can trace all decisions via decision log

**Alternative Flow:**
- Custom file upload disabled in v1
- User sees message: "Custom upload available in full version"

---

## ✅ Technical Acceptance Criteria

**AC-1: End-to-End Processing**
- System processes 12-requirement SOC 2 checklist without manual intervention
- Input: Synthetic audit checklist (CSV/Excel) + 3 policy documents (PDF)
- Output: Gap report with coverage classifications
- Pass criteria: Complete execution without errors

**AC-2: Agent Orchestration Integrity**
- Orchestrator and Coverage Agent operate as distinct components with tool access separation enforced at code level
- Pass criteria: Orchestrator cannot directly access retrieval system; Coverage Agent cannot write to decision log

**AC-3: Self-Correction Mechanism**
- Confidence-based re-query triggers on low-confidence assessments with maximum 1 retry per requirement
- Pass criteria: ≥1 requirement triggers re-query in synthetic dataset execution

**AC-4: Gap Detection Accuracy**
- Coverage assessments match ground truth labels in policy metadata
- Ground truth: 5 "Covered", 4 "Partial", 3 "At Risk"
- Pass criteria: ≥10/12 requirements classified correctly

**AC-5: Retrieval Abstraction**
- Retrieval interface implemented to support swappable implementations
- Pass criteria: Agent code unchanged when swapping retrieval implementations

**AC-6: Decision Auditability**
- All Orchestrator decisions captured in append-only log with complete metadata (timestamp, requirement_id, assessment, confidence, citations, reasoning)
- Pass criteria: 100% of agent interactions logged

---

## 📊 Success Metrics

### Primary Metrics

**Gap Detection Accuracy**
- Target: ≥83% match with ground truth (10/12 requirements)
- Measures: System's ability to correctly classify coverage status

**Processing Latency**
- Target: p95 ≤60 seconds for 12-requirement analysis
- Measures: End-to-end performance from upload to report generation

**System Availability**
- Target: 99% uptime on Streamlit Cloud
- Measures: Demo accessibility

### Secondary Metrics

**Self-Correction Trigger Rate**
- Target: ≥8% of requirements (validates mechanism works)
- Measures: System's ability to identify and retry low-confidence assessments

**Decision Log Completeness**
- Target: 100% of agent interactions captured
- Measures: Auditability and traceability

### User Experience Metrics

**Demo Completion Rate**
- Target: ≥90% of sessions complete end-to-end
- Measures: User workflow success

**Error Rate**
- Target: <5% of demo runs fail
- Measures: System reliability

---

## 🛡️ Non-Functional Requirements

### Performance
- Response time: Gap report generation ≤60s (p95)
- Retrieval latency: ≤500ms per semantic search query
- UI responsiveness: Progress updates every 2-3 seconds

### Reliability
- Uptime: 99% availability (Streamlit Cloud SLA)
- Error handling: Graceful degradation on API failures with user-facing error messages
- Data persistence: Decision logs retained in session (exportable)

### Security & Privacy
- No PII collection in synthetic dataset
- API keys stored in Streamlit secrets (not in code)
- No user authentication required (public demo)

### Scalability
- v1: Single-tenant, synthetic data only
- Designed for future multi-tenant upgrade (v2)
- In-memory retrieval supports up to 100 policy chunks

### Maintainability
- Code modularity: Agents in separate files
- Clear documentation: README with architecture diagram, setup instructions
- Abstraction layers enable component evolution

---

## 🔗 Dependencies & Assumptions

### External Dependencies

**Anthropic API (Claude Sonnet 4)**
- Purpose: Agent reasoning and structured output generation
- Criticality: Required for all operations
- Risk: API outage blocks system
- Mitigation: Error handling with user-facing message, no automatic retry

**OpenAI API (Embeddings)**
- Purpose: Policy document embedding generation
- Criticality: Build-time only (pre-computed embeddings)
- Risk: Rate limiting during embedding generation
- Mitigation: Batch processing, embeddings committed to repository

**SharePoint MCP Server** *(v1.5)*
- Purpose: Live evidence retrieval from SharePoint document repositories via MCP protocol
- Criticality: Required for v1.5 SharePoint integration; not needed for v1
- Risk: Third-party MCP server availability and search quality outside system control; SharePoint content quality varies
- Mitigation: Graceful fallback to local policy store if MCP unavailable; manual spot-check of retrieval quality on representative SharePoint content before integration

**Streamlit Cloud**
- Purpose: Hosting platform for demo
- Criticality: Required for public accessibility
- Risk: Free tier usage limits
- Mitigation: Monitor usage, upgrade to paid tier if needed

### Technical Dependencies

- Python 3.10+: Core runtime
- pdfplumber: PDF text extraction
- numpy: Vector operations for semantic search
- pandas: Audit checklist parsing

### Key Assumptions

1. **Synthetic dataset is sufficient** for v1 validation (no real customer data needed)
2. **Streamlit Cloud free tier** supports expected demo traffic
3. **Pre-computed embeddings** eliminate runtime OpenAI dependency
4. **In-memory retrieval** performs adequately for <100 policy chunks
5. **SOC 2 framework** is representative enough to validate approach

---

## ⚠️ Key Risks & Mitigations

### Risk 1: Agent System Collapses into Single Agent

**Symptom:** Orchestrator directly queries retrieval system, Coverage Agent becomes meaningless wrapper

**Mitigation:**
- Tool access separation enforced architecturally
- Acceptance testing validates agent isolation

**Severity:** High (invalidates multi-agent hypothesis)

---

### Risk 2: Hallucinated Coverage Claims

**Symptom:** Agent claims "Covered" when evidence doesn't support it

**Mitigation:**
- Citations required for all "Covered" assessments
- Confidence scoring mandatory in all responses
- Ground truth validation in acceptance testing

**Severity:** High (undermines trust in system)

---

### Risk 3: Retrieval Quality

**Symptom:** Semantic search misses relevant policy chunks

**Mitigation:**
- Pre-validated retrieval on synthetic dataset before agent integration
- Manual spot-check of top-5 retrieved chunks per requirement
- Entity metadata enables future upgrade to graph-hybrid retrieval

**Severity:** Medium (degrades accuracy but doesn't break system)

---

### Risk 4: Demo Dataset Too Easy/Hard

**Symptom:** System marks everything "Covered" (too easy) or "At Risk" (too hard)

**Mitigation:**
- Balanced dataset design with known coverage gaps
- External review of dataset difficulty
- Iterative tuning based on initial results

**Severity:** Medium (affects demo credibility)

---

### Risk 5: Streamlit Cloud Deployment Fails

**Symptom:** Works locally but breaks on Streamlit Cloud

**Mitigation:**
- Pre-compute embeddings (no runtime OpenAI calls)
- Test with minimal dependencies first
- Use Streamlit secrets for API keys
- Deploy early to catch issues before full integration

**Severity:** Medium (delays demo availability)

---

## 🚀 Roadmap Beyond v1

### v1.5 — Connect to Real Evidence
**Focus:** Replace synthetic data with live SharePoint evidence via MCP
- SharePoint MCP server integration — Coverage Agent gains SharePoint as a retrieval source alongside local policy store
- Result merging: evidence ranked and deduplicated across local PDFs and SharePoint results
- FAISS retrieval upgrade (validates swappable abstraction layer under real-world load)
- PDF export for gap report
- Performance optimization (caching, parallel processing) to accommodate live retrieval latency

**Key Architectural Change:** The Coverage Agent's tool surface expands to include a SharePoint MCP tool. The Retrieval Abstraction Layer merges results from both sources. Orchestrator and decision log are unchanged. MCP eliminates the OAuth complexity that previously deferred this to v2.

### v2.0 — Institutional Memory
**Focus:** Organizational knowledge that persists across audit cycles
- Knowledge graph layer modeling relationships between controls, policies, findings
- Graph-hybrid retrieval for relationship-aware evidence matching
- Multi-cycle memory: system retains what was flagged last year, who owned remediation, what evidence satisfied the auditor
- Outreach Agent for cross-functional coordination

### v3.0 — Production Scale
**Focus:** Enterprise readiness, multi-tenant deployment
- Production knowledge graph (Neo4j)
- Cloud vector database (Pinecone)
- Multi-tenancy with per-customer isolation
- Framework expansion (SOC 1, HIPAA, ISO 27001, FedRAMP)
- Persistent audit workspaces

**Key Insight:** The knowledge graph enables true institutional memory—the system remembers what was flagged last year, which controls are interdependent, and which policies map to which frameworks. Combined with the SharePoint integration established in v1.5, this transforms the system from "audit analysis tool" to "organizational compliance memory."

---

### Risk 6: SharePoint MCP Server Quality *(v1.5)*

**Symptom:** MCP server returns low-relevance results or is unavailable, degrading coverage assessment accuracy on live evidence

**Mitigation:**
- Graceful fallback to local policy store if MCP server is unavailable
- Manual spot-check of retrieval quality on representative SharePoint content before v1.5 integration
- Result confidence scoring flags low-quality MCP retrievals for human review

**Severity:** Medium (degrades accuracy but doesn't break system; fallback maintains v1 functionality)

---

## 📋 Open Questions

**Q1:** Should v1 support multiple audit frameworks (SOC 2 vs SOC 1)?
- **Current Decision:** No - v1 is SOC 2 Type II only to limit scope
- **Rationale:** Proving multi-agent pattern is priority; framework expansion is v2

**Q2:** What happens if all 12 requirements are marked "At Risk"?
- **Status:** TBD - need to define failure modes and user guidance
- **Next Step:** Define minimum viable coverage threshold

**Q3:** Should decision log be downloadable or only viewable?
- **Decision:** Downloadable (JSON export)
- **Rationale:** Supports audit trail and external analysis

**Q4:** How do we handle API failures during live demo?
- **Current Approach:** Display error message, maintain partial results if possible
- **Next Step:** Define graceful degradation scenarios

**Q5:** Which SharePoint MCP server should v1.5 use, and how is it hosted?
- **Status:** TBD — options include Microsoft's first-party MCP server, third-party implementations, or a self-managed server
- **Next Step:** Evaluate available SharePoint MCP servers against retrieval quality, auth model, and hosting requirements before v1.5 planning

---

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Agent Orchestration** | Python 3.10+ | Standard for AI projects, extensive library ecosystem |
| **LLM** | Claude Sonnet 4 | Provides structured output for agent communication protocol, balances reasoning quality with cost |
| **SharePoint Integration** *(v1.5)* | SharePoint MCP Server | Eliminates OAuth complexity; Coverage Agent gains SharePoint as a native tool without agent code changes |
| **Semantic Search** | Vector embeddings | Captures semantic meaning beyond keyword matching |
| **Document Processing** | pdfplumber | Reliable PDF text extraction |
| **UI** | Streamlit | Rapid prototyping, built-in deployment to cloud |
| **Deployment** | Streamlit Cloud | Free tier, auto-deploy from GitHub, minimal configuration |
| **Version Control** | GitHub (public) | Open source, community visibility |

---

**Document Version:** 1.1  
**Last Updated:** May 15, 2026  
**Owner:** Lalitha  
**Stakeholders:** [If applicable]
