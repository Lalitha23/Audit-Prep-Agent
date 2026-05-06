import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from .agent_base import Agent
from ..retrieval.retrieval_interface import RetrievalEngine


def _load_env() -> None:
    search = Path(__file__).resolve().parent
    for _ in range(8):
        if (search / ".env").exists():
            load_dotenv(search / ".env", override=False)
            return
        git = search / ".git"
        if git.is_file():
            gitdir = Path(git.read_text().split("gitdir:")[1].strip())
            real_root = gitdir.parent.parent.parent
            if (real_root / ".env").exists():
                load_dotenv(real_root / ".env", override=False)
            return
        if git.is_dir():
            if (search / ".env").exists():
                load_dotenv(search / ".env", override=False)
            return
        search = search.parent


_load_env()

_SYSTEM_PROMPT = """You are a SOC 2 Type II compliance analyst.

You will be given:
1. A SOC 2 requirement (requirement_id, requirement_text, control_objective)
2. Policy document excerpts retrieved from the company's policy corpus

Your task is to assess whether the retrieved policy evidence covers the requirement.

Respond with ONLY valid JSON in this exact structure:
{
  "assessment": "Covered" | "Partial" | "At Risk",
  "confidence": "high" | "medium" | "low",
  "citations": [
    {"source": "<filename>", "excerpt": "<30-50 word quote>", "score": <float>}
  ],
  "reasoning": "<2-4 sentence explanation of your assessment>",
  "suggested_recheck_terms": ["<term1>", "<term2>"]
}

Guidelines:
- "Covered": Policy explicitly and completely addresses all key elements of the requirement
- "Partial": Requirement is mentioned or partially addressed but key elements are missing
- "At Risk": No meaningful coverage found in the retrieved evidence
- citations: include only excerpts that directly support your assessment (max 3)
- suggested_recheck_terms: 2-4 specific search terms to surface targeted policy evidence
  - ALWAYS include when confidence is "low"
  - ALWAYS include when assessment is "Partial" and confidence is "medium" (ambiguous partial coverage warrants a second look)
  - Omit otherwise
- Keep reasoning factual and grounded in the evidence provided
"""


def _build_user_prompt(requirement: Dict, chunks: List[Dict]) -> str:
    evidence_blocks = []
    for i, chunk in enumerate(chunks, 1):
        evidence_blocks.append(
            f"[Evidence {i}] Source: {chunk['source']} | Score: {chunk['score']:.4f}\n"
            f"{chunk['text'][:600]}"
        )
    evidence_str = "\n\n".join(evidence_blocks) or "No evidence retrieved."

    return (
        f"REQUIREMENT\n"
        f"ID: {requirement.get('requirement_id', 'N/A')}\n"
        f"Category: {requirement.get('category', 'N/A')}\n"
        f"Text: {requirement.get('requirement_text', '')}\n"
        f"Control Objective: {requirement.get('control_objective', '')}\n\n"
        f"RETRIEVED POLICY EVIDENCE\n{evidence_str}"
    )


class CoverageAgent(Agent):
    """Assesses whether policy documents cover a given SOC 2 requirement.

    For each requirement it:
    1. Retrieves the top-5 most relevant policy chunks via the retrieval engine
    2. Asks Claude to assess coverage given the requirement and evidence
    3. Returns a structured assessment with confidence, citations, and reasoning

    Args:
        retrieval_engine: A RetrievalEngine implementation (e.g. InMemoryRetrieval).
        model:            Claude model to use for assessment.
    """

    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        super().__init__(
            name="CoverageAgent",
            role="Assess SOC 2 requirement coverage against policy evidence",
            tools=["retrieve_evidence"],
        )
        self.retrieval_engine = retrieval_engine
        self.model = model

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def process_message(self, message: Dict) -> Dict:
        """Assess a single SOC 2 requirement.

        Args:
            message: Dict with keys:
                - requirement_id   (str)
                - requirement_text (str)
                - category         (str, optional)
                - control_objective (str, optional)
                - recheck_terms    (List[str], optional) – override retrieval query

        Returns:
            Assessment dict with requirement_id, assessment, confidence,
            citations, reasoning, and optionally suggested_recheck_terms.
        """
        req_id   = message.get("requirement_id", "UNKNOWN")
        req_text = message.get("requirement_text", "")
        recheck  = message.get("recheck_terms")

        # --- 1. retrieve evidence ---
        query = " ".join(recheck) if recheck else req_text
        self.log_message("retrieve", {"requirement_id": req_id, "query": query[:120]})

        chunks = self.retrieval_engine.retrieve(query, top_k=5)
        self.log_message("retrieved", {"requirement_id": req_id, "chunk_count": len(chunks)})

        # --- 2. ask Claude to assess coverage ---
        user_prompt = _build_user_prompt(message, chunks)

        self.log_message("assess_start", {"requirement_id": req_id})
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown fences if Claude wrapped the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            self.log_message("parse_error", {"raw": raw[:200]}, level="error")
            result = {
                "assessment": "At Risk",
                "confidence": "low",
                "citations": [],
                "reasoning": "Could not parse Claude response. Manual review required.",
                "suggested_recheck_terms": [req_text[:50]],
            }

        result["requirement_id"]    = req_id
        result["retrieved_chunks"] = chunks   # expose to UI / callers
        self.log_message(
            "assessed",
            {"requirement_id": req_id, "assessment": result.get("assessment"),
             "confidence": result.get("confidence")},
        )
        return result
