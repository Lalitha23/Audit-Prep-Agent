"""
Convert policy .txt files to professionally formatted PDFs using reportlab.
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    PageBreak, Table, TableStyle
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate


POLICIES_DIR = Path(__file__).parent.parent / "data" / "synthetic" / "policies"

HEADER_COLOR = colors.HexColor("#1a3a5c")
RULE_COLOR   = colors.HexColor("#3a7abf")
BODY_COLOR   = colors.HexColor("#1a1a1a")


def build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles["doc_title"] = ParagraphStyle(
        "doc_title",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=HEADER_COLOR,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    styles["meta_label"] = ParagraphStyle(
        "meta_label",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=HEADER_COLOR,
        spaceBefore=14,
        spaceAfter=4,
    )
    styles["subsection_heading"] = ParagraphStyle(
        "subsection_heading",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=HEADER_COLOR,
        spaceBefore=8,
        spaceAfter=3,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=BODY_COLOR,
        spaceBefore=2,
        spaceAfter=2,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=BODY_COLOR,
        leftIndent=18,
        firstLineIndent=0,
        spaceBefore=1,
        spaceAfter=1,
        bulletIndent=6,
    )
    styles["sub_bullet"] = ParagraphStyle(
        "sub_bullet",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=BODY_COLOR,
        leftIndent=36,
        firstLineIndent=0,
        spaceBefore=1,
        spaceAfter=1,
        bulletIndent=24,
    )
    styles["revision_header"] = ParagraphStyle(
        "revision_header",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
        spaceBefore=10,
        spaceAfter=2,
    )
    styles["revision_row"] = ParagraphStyle(
        "revision_row",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=BODY_COLOR,
    )
    styles["separator"] = ParagraphStyle(
        "separator",
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#888888"),
    )
    return styles


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.drawRightString(doc.pagesize[0] - inch, 0.5 * inch, text)
    canvas.drawString(inch, 0.5 * inch, doc.title or "Acme Corporation — Confidential")
    canvas.restoreState()


def classify_line(line: str, styles: dict):
    """Return (style_name, text, is_spacer) for a given raw line."""
    stripped = line.rstrip()

    if not stripped:
        return None, None, True

    # Separator lines (=== or ---)
    if set(stripped.replace(" ", "")) <= {"="}:
        return "separator", stripped, False
    if set(stripped.replace(" ", "")) <= {"-"}:
        return "separator", stripped, False

    # Metadata block at top (lines like "Version: v2.1")
    # These appear before the first numbered section; caller handles them.

    # Numbered top-level section heading: "3. POLICY STATEMENTS"
    import re
    if re.match(r"^\d+\.\s+[A-Z]", stripped):
        return "section_heading", stripped, False

    # Sub-section heading: "3.1 Logical Access Controls"
    if re.match(r"^\d+\.\d+\s+\S", stripped):
        return "subsection_heading", stripped, False

    # Lettered sub-item:  "  (a) Something"
    if re.match(r"^\s+\([a-z]\)\s+", stripped):
        text = stripped.strip()
        return "sub_bullet", f"&#8226;&nbsp;&nbsp;{text}", False

    # Dash bullet "  - Something"
    if re.match(r"^\s+[-–—]\s+", stripped):
        text = stripped.strip().lstrip("-–— ").strip()
        return "bullet", f"&#8226;&nbsp;&nbsp;{text}", False

    # Revision history rows (plain indented lines after REVISION HISTORY heading)
    # Treat all other indented lines as body too.
    return "body", stripped, False


def parse_txt(txt_path: Path, styles: dict):
    """Parse a policy .txt file into a list of reportlab Flowables."""
    lines = txt_path.read_text(encoding="utf-8").splitlines()

    flowables = []
    in_header_block = True   # True until we hit the first numbered section
    header_lines = []
    in_revision = False

    import re

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # ---- separator lines ----
        if set(stripped.replace(" ", "")) <= {"="} and len(stripped) > 10:
            if in_header_block and header_lines:
                # We've accumulated the doc title block — flush it
                _flush_header(header_lines, flowables, styles)
                header_lines = []
                in_header_block = False
            else:
                flowables.append(
                    HRFlowable(width="100%", thickness=1.5, color=RULE_COLOR, spaceAfter=4)
                )
            i += 1
            continue

        if set(stripped.replace(" ", "")) <= {"-"} and len(stripped) > 10:
            flowables.append(
                HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=2)
            )
            i += 1
            continue

        # ---- header block accumulation ----
        if in_header_block:
            header_lines.append(stripped)
            i += 1
            continue

        # ---- blank line ----
        if not stripped:
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # ---- REVISION HISTORY section ----
        if "REVISION HISTORY" in stripped:
            in_revision = True
            flowables.append(Paragraph(stripped, styles["section_heading"]))
            i += 1
            continue

        if in_revision:
            # Render revision rows in a small monospaced style
            flowables.append(Paragraph(stripped, styles["revision_row"]))
            i += 1
            continue

        # ---- numbered top-level section heading ----
        if re.match(r"^\d+\.\s+[A-Z]", stripped):
            flowables.append(Paragraph(stripped, styles["section_heading"]))
            i += 1
            continue

        # ---- sub-section heading ----
        if re.match(r"^\d+\.\d+\s+\S", stripped):
            flowables.append(Paragraph(stripped, styles["subsection_heading"]))
            i += 1
            continue

        # ---- lettered sub-item (a) ----
        if re.match(r"^\s{2,}\([a-z]\)\s+", stripped):
            text = stripped.strip()
            # Collect continuation lines (indented further than (a) marker)
            while i + 1 < len(lines):
                next_line = lines[i + 1].rstrip()
                if next_line and re.match(r"^\s{6,}", next_line) and not re.match(r"^\s{2,}\([a-z]\)\s+", next_line):
                    text += " " + next_line.strip()
                    i += 1
                else:
                    break
            # Escape ampersands for reportlab
            safe = text.replace("&", "&amp;")
            flowables.append(Paragraph(f"•  {safe}", styles["sub_bullet"]))
            i += 1
            continue

        # ---- dash bullet ----
        if re.match(r"^\s{2,}[-–—]\s+", stripped):
            text = stripped.strip().lstrip("-–— ").strip()
            while i + 1 < len(lines):
                next_line = lines[i + 1].rstrip()
                if next_line and re.match(r"^\s{6,}", next_line) and not re.match(r"^\s{2,}[-]\s+", next_line):
                    text += " " + next_line.strip()
                    i += 1
                else:
                    break
            safe = text.replace("&", "&amp;")
            flowables.append(Paragraph(f"•  {safe}", styles["bullet"]))
            i += 1
            continue

        # ---- default: body paragraph ----
        # Collect continuation of wrapped body text
        text = stripped
        while i + 1 < len(lines):
            next_line = lines[i + 1].rstrip()
            if (next_line and
                    not re.match(r"^\d+\.\s+[A-Z]", next_line) and
                    not re.match(r"^\d+\.\d+\s+\S", next_line) and
                    not re.match(r"^\s{2,}\([a-z]\)\s+", next_line) and
                    not re.match(r"^\s{2,}[-]\s+", next_line) and
                    not (set(next_line.replace(" ", "")) <= {"="} and len(next_line) > 10) and
                    not (set(next_line.replace(" ", "")) <= {"-"} and len(next_line) > 10) and
                    not "REVISION HISTORY" in next_line):
                # Only merge if the current line does NOT end a logical paragraph
                # (simple heuristic: merge if prev line doesn't end sentence-finally)
                if not text.endswith((".", ":", ";")):
                    text += " " + next_line.strip()
                    i += 1
                    continue
            break
        safe = text.replace("&", "&amp;")
        flowables.append(Paragraph(safe, styles["body"]))
        i += 1

    return flowables


def _flush_header(header_lines, flowables, styles):
    """Render the top metadata block (title + key-value pairs)."""
    import re
    title_done = False
    meta_pairs = []

    for line in header_lines:
        if not line:
            continue
        # The all-caps line(s) before the first key: value are the title
        if not title_done and re.match(r"^[A-Z\s]+$", line) and len(line) > 5:
            flowables.append(Paragraph(line.strip(), styles["doc_title"]))
            title_done = True
            continue
        # Key: value metadata lines
        if ":" in line:
            flowables.append(Paragraph(line.strip(), styles["meta_label"]))

    flowables.append(Spacer(1, 6))
    flowables.append(
        HRFlowable(width="100%", thickness=2, color=RULE_COLOR, spaceAfter=8)
    )


def convert_txt_to_pdf(txt_path: Path):
    pdf_path = txt_path.with_suffix(".pdf")

    styles = build_styles()
    flowables = parse_txt(txt_path, styles)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=1.0 * inch,
        rightMargin=1.0 * inch,
        topMargin=1.0 * inch,
        bottomMargin=0.85 * inch,
        title=txt_path.stem.replace("_", " ").title(),
    )

    doc.build(flowables, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return pdf_path


def main():
    txt_files = sorted(POLICIES_DIR.glob("*.txt"))
    if not txt_files:
        print("No .txt files found in", POLICIES_DIR)
        return

    print(f"Converting {len(txt_files)} file(s) in {POLICIES_DIR}\n")
    for txt_path in txt_files:
        print(f"  {txt_path.name}  ->  ", end="", flush=True)
        pdf_path = convert_txt_to_pdf(txt_path)
        size_kb = pdf_path.stat().st_size / 1024
        print(f"{pdf_path.name}  ({size_kb:.1f} KB)")

    print("\nDone.")


if __name__ == "__main__":
    main()
