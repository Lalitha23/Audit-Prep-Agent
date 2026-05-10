"""Generate a clean vertical flow architecture diagram for AuditPrep Agent."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

OUT = "docs/architecture_diagram.png"

# ── Palette ────────────────────────────────────────────────────────────────────
LAYERS = [
    {
        "title":    "USER INTERFACE",
        "lines":    ["Streamlit UI  ·  Chat Interface  ·  Gap Report"],
        "bg":       "#1E3A8A",   # deep blue
        "fg":       "#FFFFFF",
    },
    {
        "title":    "MULTI-AGENT SYSTEM",
        "lines":    ["Orchestrator Agent  →  Coverage Agent"],
        "sub":      "Parses checklist  ·  Delegates tasks  ·  Self-correction",
        "bg":       "#1D4ED8",
        "fg":       "#FFFFFF",
    },
    {
        "title":    "SEMANTIC RETRIEVAL",
        "lines":    ["In-Memory Search  (cosine similarity)"],
        "sub":      "Policy Embeddings  ·  1 536-dim vectors",
        "bg":       "#0369A1",
        "fg":       "#FFFFFF",
    },
    {
        "title":    "EXTERNAL SERVICES",
        "lines":    ["OpenAI API  (text-embedding-3-small)   |   Anthropic API  (Claude Sonnet 4)"],
        "bg":       "#0891B2",
        "fg":       "#FFFFFF",
    },
    {
        "title":    "DATA SOURCES",
        "lines":    ["SOC 2 Checklist  (CSV)   |   Policy Documents  (PDFs)"],
        "bg":       "#0E7490",
        "fg":       "#FFFFFF",
    },
]

ARROW_LABELS = [
    "user request",
    "retrieve evidence",
    "assess coverage",
    "process data",
]

# ── Layout constants ───────────────────────────────────────────────────────────
FIG_W   = 10
BOX_W   = 8.4        # box width in data units
BOX_H   = 1.15       # box height
GAP     = 0.62       # vertical gap between boxes (for arrow)
TITLE_H = 0.30       # extra title row height inside box

n       = len(LAYERS)
total_h = n * BOX_H + (n - 1) * GAP + 0.8   # +0.8 for top/bottom margin
FIG_H   = total_h * 0.95 + 0.6

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, total_h)
ax.axis("off")
fig.patch.set_facecolor("#FFFFFF")

# ── Header ─────────────────────────────────────────────────────────────────────
ax.text(FIG_W / 2, total_h - 0.28,
        "AuditPrep Agent — System Architecture",
        ha="center", va="center", fontsize=14, fontweight="bold",
        color="#0F172A")

# ── Draw layers top → bottom ───────────────────────────────────────────────────
LEFT  = (FIG_W - BOX_W) / 2
start_y = total_h - 0.65   # top of first box

for i, layer in enumerate(LAYERS):
    y_top = start_y - i * (BOX_H + GAP)
    y_bot = y_top - BOX_H

    # ── Box ──────────────────────────────────────────────────────────────────
    rect = FancyBboxPatch(
        (LEFT, y_bot), BOX_W, BOX_H,
        boxstyle="round,pad=0.04",
        facecolor=layer["bg"], edgecolor="none",
        linewidth=0, zorder=2,
    )
    ax.add_patch(rect)

    # thin white top-stripe for the title row
    stripe = FancyBboxPatch(
        (LEFT, y_top - TITLE_H), BOX_W, TITLE_H,
        boxstyle="round,pad=0.04",
        facecolor="white", alpha=0.12, edgecolor="none",
        linewidth=0, zorder=3,
    )
    ax.add_patch(stripe)

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.text(LEFT + BOX_W / 2, y_top - TITLE_H / 2,
            layer["title"],
            ha="center", va="center",
            fontsize=10.5, fontweight="bold",
            color=layer["fg"], zorder=4)

    # ── Body lines ────────────────────────────────────────────────────────────
    body_center = y_bot + (BOX_H - TITLE_H) / 2

    has_sub = "sub" in layer
    main_line = layer["lines"][0]

    if has_sub:
        ax.text(LEFT + BOX_W / 2, body_center + 0.13,
                main_line,
                ha="center", va="center",
                fontsize=9, color=layer["fg"], zorder=4)
        ax.text(LEFT + BOX_W / 2, body_center - 0.13,
                layer["sub"],
                ha="center", va="center",
                fontsize=8, color=layer["fg"], alpha=0.82, zorder=4,
                style="italic")
    else:
        ax.text(LEFT + BOX_W / 2, body_center,
                main_line,
                ha="center", va="center",
                fontsize=9, color=layer["fg"], zorder=4)

    # ── Arrow below (except last layer) ──────────────────────────────────────
    if i < n - 1:
        label = ARROW_LABELS[i]
        ax_x  = FIG_W / 2
        ay_start = y_bot - 0.04
        ay_end   = y_bot - GAP + 0.06

        ax.annotate("",
            xy=(ax_x, ay_end), xytext=(ax_x, ay_start),
            arrowprops=dict(
                arrowstyle="->,head_width=0.28,head_length=0.14",
                color="#64748B", lw=1.8,
            ), zorder=5)

        ax.text(ax_x + 0.22, (ay_start + ay_end) / 2,
                label,
                ha="left", va="center",
                fontsize=8, color="#64748B", style="italic", zorder=5)

# ── Footer ─────────────────────────────────────────────────────────────────────
ax.text(FIG_W / 2, 0.15,
        "SOC 2 Type II Gap Analysis  ·  Multi-Agent AI System",
        ha="center", va="center",
        fontsize=7.5, color="#94A3B8")

plt.tight_layout(pad=0.3)
plt.savefig(OUT, dpi=150, bbox_inches="tight",
            facecolor="#FFFFFF", edgecolor="none")
print(f"Saved → {OUT}")
