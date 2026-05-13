# AuditPrep Agent
Multi-agent audit gap analysis system

## Live App

[https://audit-prep-agent.streamlit.app](https://audit-prep-agent.streamlit.app)

## Project Structure

```
auditprep-agent/
├── data/
│   ├── synthetic/          # Synthetic audit documents for demonstration
│   │   ├── policies/       # Policy documents (PDF/text)
│   │   ├── checklists/     # Audit checklists
│   │   └── metadata/       # Document metadata
│   └── embeddings/         # Pre-computed vector embeddings (gitignored)
├── src/
│   ├── agents/             # Multi-agent orchestration layer
│   │   ├── agent_base.py   # Shared base class for all agents
│   │   ├── orchestrator.py # Root orchestrator agent
│   │   └── coverage_agent.py # SOC 2 coverage analysis agent
│   ├── retrieval/          # Semantic retrieval abstraction
│   │   ├── retrieval_interface.py   # Abstract retrieval interface
│   │   └── in_memory_retrieval.py  # In-memory vector store implementation
│   ├── utils/              # Shared utilities
│   │   ├── pdf_parser.py   # PDF text extraction
│   │   ├── chunking.py     # Document chunking strategies
│   │   └── embedding_generator.py  # Embedding generation via OpenAI
│   └── ui/
│       └── streamlit_app.py  # Streamlit frontend
└── scripts/
    ├── generate_embeddings.py  # Precompute and cache embeddings
    └── validate_retrieval.py   # Smoke-test retrieval quality
```

## v1 Scope
- SOC 2 Type II audit gap analysis
- Synthetic dataset demonstration
- Multi-agent orchestration (Orchestrator + Coverage Agent)
- Semantic retrieval with abstraction layer
