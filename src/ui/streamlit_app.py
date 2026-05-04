import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from src.utils.embedding_generator import EmbeddingGenerator
from src.retrieval.in_memory_retrieval import InMemoryRetrieval
from src.agents.orchestrator import Orchestrator

st.set_page_config(page_title="AuditPrep Agent", layout="wide")
st.title("AuditPrep Agent")
st.caption("SOC 2 Type II Audit Gap Analysis")


@st.cache_resource
def build_orchestrator() -> Orchestrator:
    generator = EmbeddingGenerator()
    retrieval = InMemoryRetrieval(embedding_generator=generator)
    return Orchestrator(retrieval=retrieval)


orchestrator = build_orchestrator()

query = st.text_input("Enter an audit query:", placeholder="e.g. access control policies")

if st.button("Analyze") and query:
    with st.spinner("Running analysis..."):
        result = orchestrator.run(query)
    st.json(result)
