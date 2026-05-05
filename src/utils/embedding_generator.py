"""
Embedding generation utility using the OpenAI Embeddings API.

Loads OPENAI_API_KEY from a .env file in the project root (or the environment).
"""

import os
import time
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError

# Search for .env upward from this file; also check the canonical repo root
# (worktrees have a different path than the main working tree)
def _find_and_load_env() -> None:
    search = Path(__file__).resolve().parent
    for _ in range(8):
        candidate = search / ".env"
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return
        search = search.parent
    # Fallback: try the real repo root via git worktree resolution
    repo_root = Path(__file__).resolve()
    for _ in range(8):
        git_dir = repo_root / ".git"
        # worktree .git is a file pointing at the real repo
        if git_dir.is_file():
            real_root = Path(git_dir.read_text().split("gitdir:")[1].strip()).parent.parent
            candidate = real_root / ".env"
            if candidate.exists():
                load_dotenv(candidate, override=False)
                return
        if git_dir.is_dir():
            candidate = repo_root / ".env"
            if candidate.exists():
                load_dotenv(candidate, override=False)
            return
        repo_root = repo_root.parent

_find_and_load_env()

# Pricing constants (as of 2024-01)
_COST_PER_1K_TOKENS = 0.00002   # text-embedding-3-small
_WORDS_PER_TOKEN    = 0.75       # rough approximation: 1 token ≈ 0.75 words
_RETRY_DELAY_SEC    = 2.0        # base delay on rate-limit retry
_MAX_RETRIES        = 3


def _estimate_tokens(text: str) -> int:
    """Approximate token count from word count."""
    return max(1, int(len(text.split()) / _WORDS_PER_TOKEN))


def generate_embeddings(
    chunks: List[Dict],
    model: str = "text-embedding-3-small",
) -> List[Dict]:
    """Generate embeddings for a list of chunk dicts via the OpenAI API.

    Each chunk must have a "text" field.  The function adds an "embedding"
    field (list of floats, 1536-dimensional for text-embedding-3-small) to
    every chunk and returns the enriched list.

    Args:
        chunks: List of chunk dicts as produced by chunk_text() /
                tag_chunk_entities().
        model:  OpenAI embedding model name.  Defaults to
                "text-embedding-3-small" (1536 dims, cheapest option).

    Returns:
        Same list with "embedding" added to each dict.

    Raises:
        EnvironmentError: If OPENAI_API_KEY is not set.
        RuntimeError:     If the API call fails after all retries.

    Examples:
        >>> chunks = [{"chunk_id": "x_001", "text": "hello world", ...}]
        >>> result = generate_embeddings(chunks)
        >>> len(result[0]["embedding"])
        1536
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or export it in your shell."
        )

    client = OpenAI(api_key=api_key)
    total = len(chunks)

    # --- cost estimate ---
    total_tokens = sum(_estimate_tokens(c.get("text", "")) for c in chunks)
    estimated_cost = (total_tokens / 1000) * _COST_PER_1K_TOKENS
    print(f"Embedding {total} chunk(s) with {model}")
    print(f"  Estimated tokens : {total_tokens:,}")
    print(f"  Estimated cost   : ${estimated_cost:.5f}")
    print()

    results: List[Dict] = []
    actual_tokens = 0

    for i, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "")
        print(f"  Processing chunk {i}/{total}  ({chunk.get('chunk_id', '?')})...", end=" ", flush=True)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = client.embeddings.create(input=text, model=model)
                embedding = response.data[0].embedding
                tokens_used = response.usage.total_tokens
                actual_tokens += tokens_used
                enriched = dict(chunk)
                enriched["embedding"] = embedding
                results.append(enriched)
                print(f"done ({tokens_used} tokens)")
                break

            except RateLimitError:
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAY_SEC * attempt
                    print(f"rate-limited, retrying in {delay}s...", end=" ", flush=True)
                    time.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Rate limit exceeded for chunk {i} after {_MAX_RETRIES} retries."
                    )

            except APIError as exc:
                raise RuntimeError(
                    f"OpenAI API error on chunk {i}: {exc}"
                ) from exc

        # Small courtesy delay to stay well under rate limits
        if i < total:
            time.sleep(0.1)

    actual_cost = (actual_tokens / 1000) * _COST_PER_1K_TOKENS
    print()
    print(f"Embedding complete.")
    print(f"  Actual tokens used : {actual_tokens:,}")
    print(f"  Actual cost        : ${actual_cost:.5f}")

    return results


# ---------------------------------------------------------------------------
# Keep the original class-based interface for backwards compatibility
# ---------------------------------------------------------------------------

class EmbeddingGenerator:
    """Thin wrapper around the OpenAI client (original interface)."""

    def __init__(self, model: str = "text-embedding-3-small"):
        api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self.model = model

    def embed(self, text: str) -> List[float]:
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]
