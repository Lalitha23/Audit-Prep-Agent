from pathlib import Path
from typing import Dict, List, Union
import pdfplumber


def parse_pdf(path: Union[str, Path]) -> str:
    """Extract all text from a PDF file."""
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_pdf(filepath: str) -> Dict:
    """Extract text from a PDF file, returning per-page and combined text.

    Args:
        filepath: Absolute or relative path to the PDF file.

    Returns:
        A dict with keys:
          - "filename"  (str)  : basename of the file
          - "pages"     (list) : list of {"page_number": int, "text": str}
          - "full_text" (str)  : all pages joined with newlines

    Raises:
        Nothing — errors are caught and returned as an "error" key so callers
        can handle them without try/except at the call site.

    Examples:
        >>> result = extract_text_from_pdf("data/synthetic/policies/access_control_policy.pdf")
        >>> result["filename"]
        'access_control_policy.pdf'
        >>> len(result["pages"]) > 0
        True
        >>> "ACCESS CONTROL" in result["full_text"]
        True

        Error case — file not found:
        >>> result = extract_text_from_pdf("missing.pdf")
        >>> "error" in result
        True
    """
    path = Path(filepath)
    filename = path.name

    if not path.exists():
        return {
            "filename": filename,
            "pages": [],
            "full_text": "",
            "error": f"File not found: {filepath}",
        }

    try:
        pages: List[Dict] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({"page_number": i, "text": text})

        full_text = "\n".join(p["text"] for p in pages if p["text"])

        return {
            "filename": filename,
            "pages": pages,
            "full_text": full_text,
        }

    except Exception as exc:
        return {
            "filename": filename,
            "pages": [],
            "full_text": "",
            "error": f"Extraction failed: {exc}",
        }
