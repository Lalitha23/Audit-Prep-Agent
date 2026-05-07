# AuditPrep Agent
Multi-agent audit gap analysis system

## Local Development

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your API keys
4. Run: `streamlit run src/ui/streamlit_app.py`

## Streamlit Cloud Deployment

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set the main file path to `src/ui/streamlit_app.py`
4. Open **Settings → Secrets** in the app dashboard and paste the contents of `.streamlit/secrets.toml.example` with your real keys filled in — do **not** upload `secrets.toml` directly
5. Click **Deploy**

Live app: _URL will be added after first deployment_

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

## Notes

> **Embeddings file**: `data/embeddings/policy_embeddings.json` (496 KB) is committed to the repo to enable Streamlit Cloud deployment without requiring an OpenAI API key at build time. If you add new policy documents locally, regenerate it with `python scripts/generate_embeddings.py` and commit the updated file.

## v1 Scope
- SOC 2 Type II audit gap analysis
- Synthetic dataset demonstration
- Multi-agent orchestration (Orchestrator + Coverage Agent)
- Semantic retrieval with abstraction layer
