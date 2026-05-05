from pathlib import Path
from typing import Dict, List

# ~375 words ≈ 500 tokens (GPT-style tokenisation approximation)
_WORDS_PER_TOKEN_CHUNK = 375
_WORDS_PER_OVERLAP = 50

_EVIDENCE_TYPES: Dict[str, str] = {
    "access control policy":     "technical_control",
    "information security policy": "administrative_control",
    "vendor management policy":  "documentation",
}


def chunk_text(
    text: str,
    source_filename: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict]:
    """Split *text* into overlapping word-based chunks, preserving paragraph breaks.

    The function first splits on double-newlines to respect paragraph boundaries,
    then packs paragraphs into windows of *chunk_size* tokens (≈ words * 375/500).
    When a single paragraph is larger than the window it is split by words directly.
    Adjacent chunks share *overlap* words of context.

    Args:
        text:            Full document text (e.g. from extract_text_from_pdf).
        source_filename: Basename of the originating PDF (used in chunk_id and
                         "source" field).
        chunk_size:      Target chunk size in tokens. Default 500.
        overlap:         Token overlap between consecutive chunks. Default 50.

    Returns:
        List of chunk dicts, each with keys:
            chunk_id   – "<stem>_chunk_<NNN>"
            source     – source_filename
            text       – chunk text
            char_start – character offset of first character in *text*
            char_end   – character offset one past the last character
            word_count – number of whitespace-delimited words in the chunk

    Examples:
        >>> chunks = chunk_text("word " * 800, "example.pdf")
        >>> chunks[0]["chunk_id"]
        'example_chunk_001'
        >>> chunks[0]["word_count"] <= 375
        True
        >>> len(chunks) > 1
        True
    """
    # Convert token targets to approximate word counts
    word_window  = int(chunk_size  * _WORDS_PER_TOKEN_CHUNK / 500)  # 375
    word_overlap = int(overlap     * _WORDS_PER_TOKEN_CHUNK / 500)  # 37 (~50 tokens)

    stem = Path(source_filename).stem  # "access_control_policy"

    # --- 1. split into paragraphs, tracking char offsets ---
    paragraphs: List[Dict] = []
    pos = 0
    for para in text.split("\n\n"):
        start = pos
        end   = pos + len(para)
        words = para.split()
        if words:
            paragraphs.append({"text": para, "words": words, "start": start, "end": end})
        pos = end + 2  # account for the "\n\n" separator

    # --- 2. pack paragraphs into word-bounded chunks ---
    raw_chunks: List[Dict] = []   # {"words": [...], "char_start": int, "char_end": int}

    current_words: List[str] = []
    current_start = 0
    current_end   = 0

    for para in paragraphs:
        if not current_words:
            current_start = para["start"]

        # Would adding this paragraph overflow the window?
        if current_words and len(current_words) + len(para["words"]) > word_window:
            # Flush current buffer
            raw_chunks.append({
                "words":      current_words[:],
                "char_start": current_start,
                "char_end":   current_end,
            })

            # Seed overlap from the tail of the flushed chunk
            overlap_words  = current_words[-word_overlap:] if word_overlap else []
            current_words  = overlap_words + para["words"]
            current_start  = para["start"]
            current_end    = para["end"]
        else:
            current_words.extend(para["words"])
            current_end = para["end"]

        # If a single paragraph is itself larger than the window, split by words
        if len(current_words) > word_window:
            word_pos = 0
            while word_pos < len(current_words):
                slice_words = current_words[word_pos : word_pos + word_window]
                slice_text  = " ".join(slice_words)
                raw_chunks.append({
                    "words":      slice_words,
                    "char_start": current_start,
                    "char_end":   current_start + len(slice_text),
                })
                word_pos += word_window - word_overlap
            current_words = []
            current_start = 0
            current_end   = 0

    # Flush any remaining words
    if current_words:
        raw_chunks.append({
            "words":      current_words,
            "char_start": current_start,
            "char_end":   current_end,
        })

    # --- 3. format output dicts ---
    chunks: List[Dict] = []
    for idx, raw in enumerate(raw_chunks, start=1):
        chunk_text_str = " ".join(raw["words"])
        chunks.append({
            "chunk_id":   f"{stem}_chunk_{idx:03d}",
            "source":     source_filename,
            "text":       chunk_text_str,
            "char_start": raw["char_start"],
            "char_end":   raw["char_end"],
            "word_count": len(raw["words"]),
        })

    return chunks


def tag_chunk_entities(chunk: Dict, policy_metadata: Dict) -> Dict:
    """Attach entity metadata to a chunk using the policy coverage map.

    Looks up *chunk["source"]* in *policy_metadata* and enriches the chunk
    with a nested "entities" dict containing the controls addressed, the
    compliance framework, the human-readable policy name, and an inferred
    evidence type.

    Args:
        chunk:           A chunk dict as returned by chunk_text().
        policy_metadata: Full contents of policy_metadata.json (a dict keyed
                         by PDF filename).

    Returns:
        The same chunk dict with an added "entities" key.  If the source file
        is not found in *policy_metadata* the entities fields are empty/unknown.

    Examples:
        >>> import json, pathlib
        >>> meta = json.loads(pathlib.Path("data/synthetic/metadata/policy_metadata.json").read_text())
        >>> chunk = {"chunk_id": "access_control_policy_chunk_001",
        ...          "source": "access_control_policy.pdf", "text": "...",
        ...          "char_start": 0, "char_end": 100, "word_count": 20}
        >>> tagged = tag_chunk_entities(chunk, meta)
        >>> tagged["entities"]["framework"]
        'SOC 2 Type II'
        >>> "CC6.1" in tagged["entities"]["controls"]
        True
    """
    source = chunk.get("source", "")
    meta   = policy_metadata.get(source, {})

    policy_title  = meta.get("title", "")
    coverage_map  = meta.get("coverage_map", {})
    controls      = list(coverage_map.keys())

    # Infer evidence type from policy title (case-insensitive)
    evidence_type = _EVIDENCE_TYPES.get(policy_title.lower(), "general_policy")

    tagged = dict(chunk)
    tagged["entities"] = {
        "controls":      controls,
        "framework":     "SOC 2 Type II",
        "policy_name":   policy_title,
        "evidence_type": evidence_type,
    }
    return tagged
