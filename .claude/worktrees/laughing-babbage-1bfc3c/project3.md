# AuditPrep Agent — Multi-Agent Audit Readiness System

## Origin Story

In enterprise government compliance SaaS, audit prep is a coordination problem disguised as a documentation problem. I saw this firsthand at Maximus, where I owned the Provider Data Management System (PDMS) — the platform that processed Medicaid and Medicare provider enrollments for state agencies. Our environment was audited by major firms on combined SOC 1 and SOC 2 scopes, depending on the contract.

The same audit vendor audits multiple service providers — Maximus, Conduent, and others — against overlapping but distinct compliance frameworks. Every audit cycle, compliance teams across these companies do nearly identical work: parse the auditor's checklist, hunt down policy evidence across SharePoint, Jira and email, chase cross-functional teams for missing documentation, and assemble the response package.

The hard part isn't the analysis. It's the coordination: tracking down evidence scattered across teams, surfacing gaps before the auditor does, and routing asks to the right owners.

This project is my attempt to redesign that workflow with a multi-agent system: an orchestrator that plans the work, a coverage specialist that analyzes evidence, and a roadmap toward outreach agents that handle the cross-functional asks. It's also where I wanted to push my own AI builder skills — beyond the single-agent MCP work in my Job Application Lifecycle Agent into genuine multi-agent orchestration with a roadmap toward organizational memory.

## The Problem

Compliance teams preparing for audits face a coordination nightmare that no existing tool solves end-to-end:

**Evidence is scattered.** Internal policies live in SharePoint, past audit findings live in PDFs, current audit checklists arrive as Excel files from the vendor. There's no single source of truth.

**Coverage gaps are invisible until it's too late.** Teams discover they're missing evidence for a control during the audit response window — when they have days, not weeks, to chase it down.

**Past findings aren't institutional memory.** The same gaps get flagged audit after audit because previous findings sit in archives, not in workflow.

**Cross-functional asks are manual and slow.** When evidence sits with another team — engineering, HR, security — compliance leads draft individual emails, follow up, escalate. This is the most time-consuming part of audit prep and the least intellectually engaging.

**Generic search doesn't work.** Audit checklists use compliance vocabulary ("logical access controls") while internal policies use operational vocabulary ("Active Directory permissions"). Keyword search misses the match. Vector search on its own helps, but doesn't solve the coordination layer.

The result: compliance teams spend the majority of audit prep on coordination tasks that an agentic system could orchestrate.

## Target User

**Primary user:** Compliance lead or compliance manager at an enterprise SaaS company operating in a regulated industry — government services, healthcare, financial services. Specifically, someone preparing for a SOC 2 Type II audit (or combined SOC 1 / SOC 2 audit in government compliance contexts).

**User context:**
- Owns the audit response on behalf of their company
- Manages 5-15 cross-functional contributors who own specific control areas
- Currently uses spreadsheets, SharePoint folders, and email to track audit prep
- Has tried generic GRC platforms (Vanta, Drata, OneTrust) but finds them either too expensive, too rigid, or not customizable for their specific framework needs
- Comfortable with AI tools but skeptical of black-box automation in a regulated environment

## Product Vision

A long-term picture worth building toward, not just a prototype:

A multi-agent system that becomes the institutional memory and coordination layer for enterprise compliance teams. The system maintains organizational knowledge across audit cycles — it knows what was flagged last year, who owned the remediation, what evidence satisfied the auditor, and what's at risk this cycle. The orchestrator coordinates evidence collection, drafts cross-functional asks, tracks responses, and surfaces gaps before they become findings.

In its mature form, the system isn't just helping with one audit — it's the connective tissue that makes audit prep continuous instead of episodic.

## Core Value Proposition

**For compliance leads preparing for SOC 2 audits**, AuditPrep Agent is **a multi-agent system that orchestrates evidence collection and gap analysis**, **unlike spreadsheets and generic GRC platforms** that leave coordination work to the human, **our system delegates analysis and outreach to specialized agents while keeping the human in control of high-stakes decisions**.

## v1 Scope ( Build Now)

The prototype proves the multi-agent orchestration pattern with the smallest viable scope. Everything in v1 is functional, end-to-end. No mocks beyond synthetic data.

**Included in v1:**
- Two agents: Orchestrator and Coverage Agent
- One document type for analysis: internal policies (PDF)
- One audit checklist: SOC 2 Type II Trust Services Criteria subset (10-15 sample requirements)
- RAG pipeline with Pinecone for evidence retrieval
- Structured JSON message protocol between agents
- Confidence-based self-correction loop (one re-query maximum per requirement)
- Append-only decision log as episodic memory
- Final gap report with three categories: Covered, Partial, At Risk
- Human-in-the-loop checkpoint: user reviews report before export
- Simple Streamlit UI showing live agent conversation during processing
- n8n orchestration wrapper (Phase 2 of v1, after Python core works)

**Explicitly out of scope for v1:**
- Outreach Agent (deferred to v2)
- Risk Agent for past findings (deferred to v2)
- Multi-cycle self-correction (single re-query is enough to prove the pattern)
- Real customer data (synthetic data only)
- Authentication, multi-tenancy, persistent storage beyond decision log


## v1.5 — Where the work actually lives

### The pain I lived

At Maximus, audit prep had a recurring rhythm I'll never forget. The auditor would send the checklist. I'd open a fresh SharePoint folder and start the gather phase. Cue the emails: "Hey, can you send me the latest access control policy?" "Where's the current vendor risk assessment?" "Is this version of the BCP still active?"

The evidence existed. It was in SharePoint. It just wasn't in MY SharePoint folder. Every audit cycle, the compliance team did the same thing: hunt down evidence that already lived somewhere accessible, copy it into the audit response folder, and hope we got the latest version.

The friction wasn't in the analysis. It was in the gathering. And the gathering was almost entirely a coordination tax — knowing where things lived, who owned them, and whether what we had was current.

A tool that requires me to upload documents into it is asking me to recreate my entire document estate every audit cycle. That's the friction I was trying to escape, not solve again in a new UI.

### The insight

Compliance evidence lives where the work lives — SharePoint, OneDrive, Teams. The audit prep tool needs to operate inside that environment, not adjacent to it. The agents shouldn't ask for documents. They should go find them.

This single shift changes the system's identity:
- v1 (upload): "an audit analysis tool"
- v1.5 (SharePoint connected): "an audit coordination agent that operates inside the company's existing document estate"

The compliance lead's job stops being "gather evidence and feed it to the tool." It becomes "tell the agent where to look, then review what it finds."

### What v1.5 adds

**SharePoint connector for the Coverage Agent**
- Coverage Agent gains a new tool: `search_sharepoint(query, scope)` 
- Scope can be a specific site, library, or folder path provided by the user during setup
- Agent retrieves documents semantically: "Find access control policies in the IT Security site"
- Documents are streamed into the existing ingest pipeline (chunk → embed → Pinecone)

**Document freshness awareness**
- Coverage Agent surfaces last-modified dates with every citation
- Stale policies (older than configurable threshold) flagged automatically
- Solves a real audit prep failure mode: presenting outdated evidence

**Folder structure as user input**
- Setup asks the compliance lead: "Where do your policies live?" "Where do past findings live?"
- Stored as a configuration artifact — once set, the agent navigates from there
- Matches how compliance leads actually think about their document estate

**Authentication via Microsoft Graph + MSAL OAuth**
- Scope-limited permissions: read access to specified sites and libraries only
- No write access in v1.5 — the agent reads, the human still owns the audit response folder

### Why this matters for the product

**Real workflow fit.** Compliance teams stop having to recreate their document estate for every audit. The tool meets the work where it already lives.

**The "stale evidence" problem solves itself.** Every citation comes with a last-modified date. The agent can flag policies that haven't been updated since the last audit cycle — exactly the kind of issue that becomes an audit finding when missed.

**The agent becomes genuinely autonomous.** Tool use deepens significantly. The Coverage Agent isn't just querying a vector store anymore — it's navigating a real corporate document estate, retrieving what's relevant, and assessing freshness. This is meaningful agentic behavior.

**v3 organizational memory becomes free.** SharePoint already contains past audit folders. Once the connector exists, the agent can reason across audit cycles without a separate Historical Knowledge Base build. The infrastructure was always there.

### Architectural design

The v1 design uses a `DocumentSource` abstraction in the ingest layer. In v1, the only implementation is `UploadedFiles`. In v1.5, a second implementation arrives: `SharePointSource`. The agent layer doesn't change — it still asks for evidence and gets chunks back. The difference is where the chunks come from.

Designing v1 with the SharePoint integration in mind ensures v1.5 is an extension, not a refactor.

### Scope discipline

v1.5 is a deliberate next sprint, not a v1 stretch goal. v1 ships with upload mode and proves the multi-agent pattern. v1.5 adds the SharePoint connector once v1 patterns are validated. This keeps v1 buildable in a tight window and gives v1.5 a clear, focused scope.

The risk of building SharePoint integration into v1: scope creep that delays the prototype and dilutes the multi-agent demonstration. The discipline of waiting: v1 ships clean, v1.5 ships fast right after.

## v2 / v3 Roadmap (Designed, Not Built)

**v2 — Cross-functional coordination**
- Add Outreach Agent that drafts evidence request emails to cross-functional teams when Coverage Agent flags missing evidence
- Add Risk Agent that analyzes past audit findings as a third document type
- Upgrade decision log to vector-based episodic memory
- Multi-cycle self-correction with a separate critic agent
- Email integration with human approval before send (HITL pattern from Job Application Lifecycle Agent)

**v3 — Organizational memory**
- Historical Knowledge Base layer: embed multiple past audit cycles into Pinecone
- Agents reason across audits, not just within one
- Pattern detection: surface recurring findings, repeat gaps, and remediation history
- Cross-audit insights: "this requirement has been flagged in 3 of the last 4 audits"
- This transforms the system from a per-audit tool into continuous compliance infrastructure

**v4 — Cross-organizational (vision, not committed)**
- Aggregated, anonymized pattern recognition across customer organizations
- Sector-specific audit intelligence
- Significant data sharing and privacy architecture required

## System Architecture

The system is layered. Each layer does what it's best at — agents make decisions, RAG provides semantic memory, infrastructure handles plumbing.

```
┌──────────────────────────────────────────────────┐
│           MULTI-AGENT LAYER                      │
│   Orchestrator + Coverage Agent                  │
│   Decisions, delegation, synthesis               │
└────────────────────┬─────────────────────────────┘
                     │ uses
                     ▼
┌──────────────────────────────────────────────────┐
│           RAG PIPELINE                           │
│   Pinecone vector store + embeddings             │
│   Semantic retrieval for evidence                │
└────────────────────┬─────────────────────────────┘
                     │ runs on
                     ▼
┌──────────────────────────────────────────────────┐
│           INFRASTRUCTURE                         │
│   Document ingest, parsing, message routing      │
│   Decision log, UI bridge                        │
└──────────────────────────────────────────────────┘
```

**End-to-end flow:**
1. User uploads SOC 2 checklist (Excel or CSV) and internal policies (PDF) via UI
2. Documents pass through ingest layer: parsed, chunked, embedded into Pinecone
3. Orchestrator reads the checklist and identifies individual requirements
4. For each requirement, Orchestrator delegates to Coverage Agent via structured JSON message
5. Coverage Agent queries Pinecone for relevant policy chunks, assesses coverage, returns structured response with confidence flag
6. Orchestrator evaluates confidence — if low, requests one re-query with refined search terms
7. Orchestrator logs each decision to the decision log
8. Once all requirements are processed, Orchestrator synthesizes the gap report
9. UI displays the report and the agent conversation log; user reviews before exporting

## Agent Specifications

### Agent 1 — Orchestrator

**Role:** Coordinates the audit analysis workflow. Plans the work, delegates analysis, evaluates results, synthesizes the final gap report.

**Tools:**
- `read_checklist(file)` — parses audit checklist into individual requirements
- `delegate_to_coverage(requirement)` — sends a single requirement to Coverage Agent
- `evaluate_confidence(coverage_response)` — checks the confidence flag returned
- `request_recheck(requirement)` — asks Coverage Agent to re-query with refined terms
- `log_decision(requirement, action, result)` — appends to decision log
- `synthesize_report(all_results)` — generates the final gap report

**Inputs:** Path to audit checklist file

**Outputs:** Final gap report (Covered, Partial, At Risk) + decision log

**Prompt design principle:** The Orchestrator's system prompt explicitly forbids direct Pinecone queries. All analysis goes through the Coverage Agent. This separation enforces the multi-agent pattern and prevents the Orchestrator from collapsing into a single agent doing everything.

### Agent 2 — Coverage Agent

**Role:** Specialist analyst. Evaluates one requirement at a time against retrieved policy evidence.

**Tools:**
- `query_pinecone(requirement_text, top_k=5)` — retrieves most relevant policy chunks
- `assess_coverage(requirement, evidence)` — internal reasoning step
- `report_back(assessment, confidence, citations)` — returns structured response

**Inputs:** Single requirement object from Orchestrator

**Outputs:** Structured JSON response with assessment, confidence, citations, reasoning

**Prompt design principle:** The Coverage Agent's system prompt requires evidence-based assessment. It must cite specific policy language. If it cannot find clear evidence, it returns "low" confidence rather than guessing. This prevents hallucinated coverage claims — critical in a compliance context.

## Communication Protocol

Agents communicate through structured JSON messages, not free-form text. This is intentional.

**Why structured messages:**
- Reliability — easier to parse, validate, and debug
- Auditability — the message log itself becomes a coordination trail
- Demo value — the agent conversation can be displayed verbatim in the UI
- Scalability — adding new agents in v2 is just adding new message types, not redesigning communication

**Orchestrator → Coverage Agent message:**
```json
{
  "from": "orchestrator",
  "to": "coverage_agent",
  "task": "assess_requirement",
  "requirement_id": "CC6.1",
  "requirement_text": "The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet the entity's objectives.",
  "context": {
    "framework": "SOC 2 Type II",
    "category": "Common Criteria"
  }
}
```

**Coverage Agent → Orchestrator response:**
```json
{
  "from": "coverage_agent",
  "to": "orchestrator",
  "requirement_id": "CC6.1",
  "assessment": "Partial",
  "confidence": "low",
  "citations": [
    {"source": "access_control_policy.pdf", "page": 3, "excerpt": "..."}
  ],
  "reasoning": "Found general access control language but no explicit reference to logical access architectures or security software inventory.",
  "suggested_recheck_terms": ["logical access architecture", "security software inventory"]
}
```

## Memory Strategy

**External memory — Pinecone vector store**
- Stores embedded chunks of internal policy documents
- Indexed with metadata: source file, page number, document type
- Queried by Coverage Agent for evidence retrieval
- This is the agent's reference library

**Episodic memory — Decision log**
- Append-only JSON file capturing every Orchestrator decision
- Records: timestamp, requirement, agent action, agent response, confidence, final assessment, whether re-query was triggered
- Provides full audit trail of the agent system's own decisions
- Becomes the demo artifact: shows that the system isn't a black box

**In-context memory**
- Each agent maintains its own conversation context within a single audit run
- Reset between audit runs in v1 (cross-session memory is a v3 feature)

**What's deliberately NOT in v1:**
- Cross-audit memory (deferred to v3)
- Vector-based episodic memory (decision log is text-based in v1; vector upgrade is v2)

## Self-Correction Logic

The system implements bounded self-correction — agents can retry, but with hard limits to prevent runaway loops or latency explosions.

```
Coverage Agent returns assessment + confidence
            │
            ▼
Orchestrator checks confidence
            │
   ┌────────┴────────┐
   ▼                 ▼
"high"            "low"
   │                 │
   │                 ▼
   │      Trigger ONE re-query with
   │      refined search terms
   │      (suggested by Coverage Agent)
   │                 │
   │                 ▼
   │      Coverage Agent re-queries
   │      Pinecone with new terms
   │                 │
   │                 ▼
   │      Returns new assessment
   │      + confidence
   │                 │
   │                 ▼
   │      If still "low":
   │      flag as "Needs Human Review"
   │                 │
   ▼                 ▼
Log decision and move to next requirement
```

**Design rationale:**
- Capping at one re-query keeps complexity bounded and latency predictable
- "Needs Human Review" is an explicit output, not a failure — it acknowledges that some requirements legitimately require human judgment
- This pattern scales: in v2, multi-cycle correction with a critic agent is added behind the same interface

## Tech Stack

Every choice is justified for the prototype scope.

**Python**
The agents, tools, and orchestration logic are all Python. Reason: ecosystem maturity for AI work, my own fluency from the Job Application Lifecycle Agent, and direct compatibility with Anthropic and Pinecone SDKs.

**Anthropic Claude API (Sonnet)**
Both Orchestrator and Coverage Agent use Claude. Reason: long context window (relevant for compliance documents), strong structured output reliability for the JSON message protocol, and consistency with my existing AI builder stack.

**Pinecone**
Vector store for policy chunk embeddings. Reason: production-grade managed service, demo-able, and the same RAG infrastructure that scales to v3 organizational memory without architectural changes.

**OpenAI text-embedding-3-small**
Embeddings for both policy chunks and Coverage Agent queries. Reason: significantly cheaper than text-embedding-3-large, performs well for compliance vocabulary, and decoupled from the Claude reasoning layer (using OpenAI for embeddings + Claude for reasoning is a common production pattern).

**pdfplumber**
PDF parsing for internal policy documents. Reason: handles tables and structured layouts better than PyPDF2, important for policy documents that often include matrices.

**n8n in v1 — added as a wrapper after Python core works**
Build approach is two phases within v1:

1. **Phase 1 — Pure Python core.** Build the multi-agent system, RAG pipeline, and self-correction loop in Python first. Faster to debug, faster to iterate, no workflow tool overhead while proving the pattern.

2. **Phase 2 — n8n orchestration wrapper.** Once the Python core works, wrap it in n8n workflows. n8n calls the Python agents as nodes, handles the document ingest pipeline, and provides the visual workflow that's demo-able to hiring managers and stakeholders.
 
**Streamlit for v1 UI**
Streamlit is the right fit for the prototype — fast to build, supports streaming output for the live agent conversation screen, and zero frontend stack overhead. A production version would move to React or Next.js for richer UX and integration capability.

## Five Agentic Dimensions Mapping

Explicit scoring against the five-dimension framework: tool use, planning and sequential reasoning, memory, self-correction, and human-in-the-loop reduction. v1 scores on all five dimensions at appropriate prototype intensity.

| Dimension | v1 Implementation | v2 Upgrade Path |
|-----------|-------------------|-----------------|
| **Tool Use** | Pinecone queries, message protocol, decision log writes | Email APIs (Outreach Agent), calendar integration |
| **Planning & Sequential Reasoning** | Orchestrator decomposes checklist into per-requirement tasks, executes in sequence | Parallel task execution, dependency-aware planning |
| **Memory** | Pinecone (external) + decision log (episodic, text-based) + in-context conversation | Vector-based episodic memory, cross-audit memory in v3 |
| **Self-Correction** | Confidence-based re-query with one-cycle cap | Multi-cycle correction with separate critic agent |
| **Human-in-the-Loop Reduction** | HITL on final report review; "Needs Human Review" flagged at confidence threshold | HITL on email send (drafted by Outreach Agent); progressive autonomy with rollback |

**Scoping rationale:**
v1 scores on every dimension at sufficient intensity to demonstrate the pattern. It does not maximize any single dimension. This is intentional — use the smallest capability that works. The roadmap documents which dimensions to deepen first based on user feedback.

## UI / UX

Three screens in v1. Each screen does one thing well.

**Screen 1 — Upload**
- Two drag-and-drop zones: SOC 2 checklist (Excel/CSV), internal policies (PDF, multiple files allowed)
- Single "Generate Gap Report" button
- Brief context line: "v1 prototype — uses synthetic data for demo. SOC 2 Type II framework."

**Screen 2 — Live Agent Conversation**
This is the demo gold. Shows the agent system thinking in real time.
- Streaming display of structured JSON messages between Orchestrator and Coverage Agent
- Color-coded by sender (Orchestrator one color, Coverage Agent another)
- Confidence indicators visible per requirement
- Re-query loops shown explicitly when triggered
- Progress indicator: "Processing requirement 7 of 15"

This screen is what makes the project differentiated. Most AI tools show you a spinner and then an answer. Showing the agent conversation surfaces the work and builds trust — exactly the right design for a regulated industry.

**Screen 3 — Gap Report**
- Three sections: Covered, Partial, At Risk
- Each requirement shows: assessment, citations to specific policy excerpts, Coverage Agent's reasoning, and any "Needs Human Review" flags
- "Export to PDF" option (v1: simple HTML-to-PDF render)
- Decision log accessible via "View Audit Trail" link

## Data Strategy

**Synthetic data only in v1.**

**Why synthetic:**
- Real audit data is sensitive — even synthetic-but-realistic data sidesteps any privacy concerns for the prototype
- Lets me build, demo, and iterate without legal or contractual constraints

**What synthetic data v1 includes:**
- One SOC 2 Type II checklist excerpt — 10-15 sample requirements drawn from public Trust Services Criteria documentation
- Three internal policy documents generated to look realistic: an Access Control Policy, an Information Security Policy, and a Vendor Management Policy. Generated with Claude, reviewed and edited for plausibility.
- Coverage gaps deliberately seeded into the policies so the agent system has real gaps to find — otherwise the demo would just say "Covered" for everything.

**Real data path:**
The architecture is designed so swapping synthetic data for real customer documents requires no code changes — just upload different files. Notes for portfolio: "Architecture supports real audit data with no changes; synthetic data used for demo to avoid privacy concerns."

## Success Criteria for v1

The prototype is "done" when:

1. **End-to-end flow works** — user uploads documents, agent system processes, gap report is generated, all without manual intervention
2. **Multi-agent pattern is observably real** — the live agent conversation screen shows distinct agents communicating via structured messages, not one model doing everything behind the scenes
3. **Self-correction triggers visibly** — at least one requirement in the demo dataset triggers a re-query, demonstrating the confidence loop
4. **Decision log is complete** — every Orchestrator decision is captured with timestamp and rationale
5. **Gap report is accurate** — for the seeded coverage gaps in the synthetic data, the system correctly flags them as "Partial" or "At Risk" with appropriate citations
6. **Demo runs in under 3 minutes** — from upload to gap report on the synthetic dataset
7. **Code is clean enough to walk through** — agent files are clearly separated, message protocol is documented, no embarrassing TODOs

## Risks & Mitigations

**Risk: The agent system collapses into a single agent doing everything.**
This is the most common failure mode for multi-agent prototypes. The Orchestrator queries Pinecone directly, the Coverage Agent stops being meaningful, and the architecture becomes single-agent in disguise.

*Mitigation:* Strict prompt design forbidding the Orchestrator from accessing Pinecone tools. Tool access is enforced at the code level, not just in prompts. Code review checks that Orchestrator's tool list does not include `query_pinecone`.

**Risk: Hallucinated coverage claims.**
In a compliance context, an agent confidently claiming a requirement is covered when it's not is a serious failure. This is the highest-stakes failure mode.

*Mitigation:* Coverage Agent prompt requires evidence citations for any "Covered" assessment. Confidence flag is mandatory. The "Needs Human Review" output is celebrated, not penalized — building a culture in the prompt that uncertainty is the correct response when evidence is unclear.

**Risk: Demo dataset is too easy or too hard.**
Synthetic data that's too easy makes the system look trivial. Too hard makes it look broken.

*Mitigation:* Seed the policies with calibrated coverage levels — some requirements clearly covered, some clearly missing, some borderline. The borderline cases are where the system shows its value through the confidence loop and "Needs Human Review" flag.

**Risk: Latency variance.**
Multi-agent systems with self-correction loops have unpredictable latency. A simple requirement might take 5 seconds; a borderline one with a re-query might take 30 seconds.

*Mitigation:* Live agent conversation UI makes the latency feel productive, not slow. Showing the work justifies the time. Progress indicators and streaming output reduce perceived wait.

**Risk: Scope creep into v2 features during v1 build.**
The roadmap lists tempting features. Outreach Agent in particular is interesting and could be built in v1 with extra effort.

*Mitigation:* Strict v1 scope discipline. Outreach Agent is explicitly out of scope. Any time temptation arises, refer back to v1 success criteria — adding features that aren't in those criteria delays shipping.

## Future Considerations

**Security and data handling**
For real customer deployment, the system needs: end-to-end encryption of uploaded documents, customer-isolated Pinecone namespaces, audit logs for every agent action, and SOC 2 compliance for the tool itself. Designing the tool that helps with SOC 2 means it needs to be SOC 2 compliant. The architecture supports this; v1 doesn't implement it.

**Multi-tenancy**
v1 is single-user. Multi-tenancy would require: customer-isolated vector namespaces, role-based access to documents and reports, and per-customer agent prompt customization for industry-specific frameworks.

**Framework expansion**
SOC 2 is the v1 framework. The same architecture supports SOC 1, HIPAA, ISO 27001, NIST 800-53, FedRAMP, and others. Each framework needs a checklist parser tailored to its format, but the agent layer is framework-agnostic. This is a significant productization opportunity.

**Auditor-facing version**
v1 targets the audit subject (compliance team at the company being audited). A natural extension is the auditor-facing version: same architecture, different orientation. Auditors could use it to triage incoming evidence packages from clients. This doubles the addressable market.

**Integration ecosystem**
Production deployment would need integrations with: SharePoint and Google Drive for policy storage, Jira and Asana for remediation tracking, Slack and Teams for cross-functional coordination, and major GRC platforms (Vanta, Drata) for status sync.

**Persistent audit sessions**
v1 treats each run as stateless. A real product needs persistent audit workspaces: named sessions per audit cycle, status that updates as evidence flows in, a dashboard the compliance lead opens daily rather than re-runs. This shifts the system from a one-time analysis tool to continuous coordination infrastructure.

**Inbound evidence handling**
The Outreach Agent (v2) drafts evidence requests to cross-functional teams. The natural counterpart is an Inbound Agent that receives responses, matches attached documents back to the original requests, routes them to the ingest pipeline, and triggers Coverage Agent re-evaluation. Outreach (push) and Inbound (pull) together form the full cross-functional coordination loop — closing the gap between "we asked for evidence" and "we have evidence and the report is updated."
