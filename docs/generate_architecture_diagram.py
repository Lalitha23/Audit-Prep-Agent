"""Generate the AuditPrep Agent system architecture diagram."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ── Palette ────────────────────────────────────────────────────────────────────
C = {
    "blue_bg":   "#DBEAFE",   # user layer bg
    "blue_bd":   "#1D4ED8",   # user layer border
    "blue_txt":  "#1E3A8A",

    "green_bg":  "#DCFCE7",   # agent layer bg
    "green_bd":  "#16A34A",
    "green_txt": "#14532D",

    "orange_bg": "#FEF3C7",   # retrieval layer bg
    "orange_bd": "#D97706",
    "orange_txt":"#78350F",

    "purple_bg": "#F3E8FF",   # external API bg
    "purple_bd": "#7C3AED",
    "purple_txt":"#4C1D95",

    "gray_bg":   "#F1F5F9",   # data sources bg
    "gray_bd":   "#64748B",
    "gray_txt":  "#1E293B",

    "arrow":     "#374151",
    "lane_bg":   "#FAFAFA",
    "lane_bd":   "#E2E8F0",
    "white":     "#FFFFFF",
}

def box(ax, x, y, w, h, label, sublabel=None,
        bg="#FFFFFF", bd="#999999", txt="#111111",
        fontsize=9, radius=0.4):
    """Draw a rounded rectangle with a label (and optional sub-label)."""
    rect = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0",
        facecolor=bg, edgecolor=bd, linewidth=1.6, zorder=3,
    )
    ax.add_patch(rect)
    if sublabel:
        ax.text(x, y + 0.12, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=txt, zorder=4)
        ax.text(x, y - 0.22, sublabel, ha="center", va="center",
                fontsize=7, color=txt, alpha=0.75, zorder=4,
                style="italic")
    else:
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=txt, zorder=4,
                multialignment="center")

def lane(ax, x, y, w, h, title, bg, bd):
    """Draw a swim-lane background rectangle with a vertical title."""
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0",
        facecolor=bg, edgecolor=bd, linewidth=1.2, zorder=1, alpha=0.45,
    )
    ax.add_patch(rect)
    ax.text(x + 0.18, y + h/2, title, ha="left", va="center",
            fontsize=7.5, fontweight="bold", color=bd,
            rotation=90, zorder=2, alpha=0.9)

def arrow(ax, x0, y0, x1, y1, label="", color="#374151", lw=1.4,
          connectionstyle="arc3,rad=0.0", double=False):
    """Draw an annotated arrow."""
    style = f"Simple,tail_width={lw},head_width={lw*5},head_length={lw*4}"
    ax.annotate("",
        xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle=style,
            color=color, lw=0,
            connectionstyle=connectionstyle,
        ), zorder=5)
    if label:
        mx, my = (x0+x1)/2, (y0+y1)/2
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=6.5, color=color,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8,
                          boxstyle="round,pad=0.15"),
                zorder=6)

# ── Canvas ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 10))
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis("off")
fig.patch.set_facecolor(C["white"])

# ── Title ──────────────────────────────────────────────────────────────────────
ax.text(8, 9.65, "AuditPrep Agent — System Architecture",
        ha="center", va="center", fontsize=14, fontweight="bold",
        color="#0F172A")

# ═══════════════════════════════════════════════════════════════════════════════
# SWIM LANES  (left-edge x, bottom y, width, height)
# ═══════════════════════════════════════════════════════════════════════════════

LANE_X  = 0.25
LANE_W  = 15.5

# Row positions (bottom of each lane)
LANE_ROWS = {
    "user":      (8.6,  0.9),   # (bottom_y, height)
    "agents":    (6.3,  2.0),
    "retrieval": (3.9,  2.2),
    "external":  (2.0,  1.7),
    "data":      (0.25, 1.55),
}

lane(ax, LANE_X, LANE_ROWS["user"][0],      LANE_W, LANE_ROWS["user"][1],
     "USER LAYER",       C["blue_bg"],   C["blue_bd"])
lane(ax, LANE_X, LANE_ROWS["agents"][0],    LANE_W, LANE_ROWS["agents"][1],
     "ORCHESTRATION LAYER", C["green_bg"], C["green_bd"])
lane(ax, LANE_X, LANE_ROWS["retrieval"][0], LANE_W, LANE_ROWS["retrieval"][1],
     "RETRIEVAL LAYER",  C["orange_bg"], C["orange_bd"])
lane(ax, LANE_X, LANE_ROWS["external"][0],  LANE_W, LANE_ROWS["external"][1],
     "EXTERNAL SERVICES",C["purple_bg"], C["purple_bd"])
lane(ax, LANE_X, LANE_ROWS["data"][0],      LANE_W, LANE_ROWS["data"][1],
     "DATA SOURCES",     C["gray_bg"],   C["gray_bd"])

# ═══════════════════════════════════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════════════════════════════════

# ── USER LAYER (y ≈ 9.1) ───────────────────────────────────────────────────────
UI_Y = 9.1
box(ax, 4.5, UI_Y, 3.6, 0.65,
    "Streamlit UI",
    "Chat interface • Document viewer • Gap report",
    C["blue_bg"], C["blue_bd"], C["blue_txt"], fontsize=9.5)

# ── ORCHESTRATION LAYER (y ≈ 7.3) ─────────────────────────────────────────────
ORCH_Y  = 7.35
COVER_Y = 7.35

box(ax, 4.5, ORCH_Y, 3.6, 0.78,
    "Orchestrator Agent",
    "Parses checklist • Delegates tasks\nTriggers self-correction",
    C["green_bg"], C["green_bd"], C["green_txt"])

box(ax, 10.5, COVER_Y, 3.6, 0.78,
    "Coverage Agent",
    "Retrieves evidence • Assesses coverage\nReturns structured results",
    C["green_bg"], C["green_bd"], C["green_txt"])

# ── RETRIEVAL LAYER (y ≈ 5.0) ─────────────────────────────────────────────────
RET_Y = 5.05

box(ax, 4.5,  RET_Y, 3.2, 0.68,
    "Retrieval Interface",
    "Abstraction layer",
    C["orange_bg"], C["orange_bd"], C["orange_txt"])

box(ax, 9.0,  RET_Y, 3.4, 0.68,
    "In-Memory Retrieval Engine",
    "Cosine similarity search",
    C["orange_bg"], C["orange_bd"], C["orange_txt"])

box(ax, 13.5, RET_Y, 3.2, 0.68,
    "Policy Embeddings Store",
    "JSON • 1536-dim vectors\n+ source metadata",
    C["orange_bg"], C["orange_bd"], C["orange_txt"])

# ── EXTERNAL SERVICES (y ≈ 2.85) ──────────────────────────────────────────────
EXT_Y = 2.88

box(ax, 4.5,  EXT_Y, 3.4, 0.65,
    "Anthropic API",
    "Claude Sonnet 4 • Coverage assessment",
    C["purple_bg"], C["purple_bd"], C["purple_txt"])

box(ax, 10.5, EXT_Y, 3.4, 0.65,
    "OpenAI API",
    "text-embedding-3-small • Semantic search",
    C["purple_bg"], C["purple_bd"], C["purple_txt"])

# ── DATA SOURCES (y ≈ 1.02) ───────────────────────────────────────────────────
DATA_Y = 1.02

box(ax, 4.5,  DATA_Y, 3.2, 0.55,
    "SOC 2 Checklist  (CSV)",
    "12 requirements • Categories\n& control objectives",
    C["gray_bg"], C["gray_bd"], C["gray_txt"], fontsize=8.5)

box(ax, 10.5, DATA_Y, 3.2, 0.55,
    "Policy Documents  (PDFs)",
    "Synthetic corpus • Access control\nIncident response • Encryption…",
    C["gray_bg"], C["gray_bd"], C["gray_txt"], fontsize=8.5)

# ═══════════════════════════════════════════════════════════════════════════════
# ARROWS — primary data flow (dark blue, solid)
# ═══════════════════════════════════════════════════════════════════════════════
AC = "#1D4ED8"   # primary flow colour
RC = "#D97706"   # retrieval flow colour
GC = "#16A34A"   # return / result flow colour

# User → Orchestrator
arrow(ax, 4.5, 8.77, 4.5, 7.75, "user request", AC)

# Orchestrator → Coverage Agent
arrow(ax, 6.3, 7.35, 8.7, 7.35, "delegate\nrequirement", AC)

# Coverage Agent → Retrieval Interface
arrow(ax, 10.5, 6.96, 4.5, 5.39, "retrieve\nevidence", RC,
      connectionstyle="arc3,rad=-0.15")

# Retrieval Interface → In-Memory Engine
arrow(ax, 6.1,  RET_Y, 7.3,  RET_Y, "", RC)

# In-Memory Engine → Embeddings Store
arrow(ax, 10.7, RET_Y, 11.9, RET_Y, "", RC)

# In-Memory Engine ← Embeddings Store  (query vectors returned)
arrow(ax, 11.9, RET_Y - 0.15, 10.7, RET_Y - 0.15, "", GC)

# Retrieval results → Coverage Agent
arrow(ax, 6.1, 5.19, 10.2, 6.96, "top-5\nchunks", GC,
      connectionstyle="arc3,rad=-0.15")

# Coverage Agent → Anthropic API
arrow(ax, 10.5, 6.96, 4.5, 3.21, "prompt +\nevidence", AC,
      connectionstyle="arc3,rad=0.25")

# Anthropic API → Coverage Agent
arrow(ax, 5.8, 3.0, 9.2, 6.96, "JSON\nassessment", GC,
      connectionstyle="arc3,rad=0.2")

# Coverage Agent → Orchestrator (results)
arrow(ax, 8.7, 7.55, 6.3, 7.55, "assessment\nresult", GC)

# Orchestrator → Streamlit UI (gap report)
arrow(ax, 4.5, 7.75, 4.5, 8.77, "gap report", GC,
      connectionstyle="arc3,rad=0.3")

# OpenAI API → Embeddings Store  (build-time)
arrow(ax, 10.5, 3.21, 13.5, 4.71, "embed\n(build-time)", "#7C3AED",
      connectionstyle="arc3,rad=-0.15")

# Data: SOC 2 Checklist → Orchestrator
arrow(ax, 4.5, 1.30, 4.5, 6.96, "load\nchecklist", C["gray_bd"],
      connectionstyle="arc3,rad=0.35")

# Data: Policy PDFs → OpenAI (embedding pipeline)
arrow(ax, 10.5, 1.30, 10.5, 2.55, "raw text\n(embed pipeline)", C["gray_bd"])

# ═══════════════════════════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════════════════════════
legend_x, legend_y = 11.6, 9.55
ax.text(legend_x, legend_y, "Legend", fontsize=8, fontweight="bold",
        color="#0F172A", va="center")

legend_items = [
    (C["blue_bd"],   "User / UI layer"),
    (C["green_bd"],  "Orchestration / Agent layer"),
    (C["orange_bd"], "Retrieval layer"),
    (C["purple_bd"], "External APIs"),
    (C["gray_bd"],   "Data sources"),
]
for i, (color, label) in enumerate(legend_items):
    lx = legend_x
    ly = legend_y - 0.38 * (i + 1)
    patch = FancyBboxPatch((lx, ly - 0.10), 0.30, 0.21,
                           boxstyle="round,pad=0",
                           facecolor=color + "33", edgecolor=color,
                           linewidth=1.2, zorder=6)
    ax.add_patch(patch)
    ax.text(lx + 0.42, ly + 0.005, label,
            fontsize=7.5, color="#374151", va="center", zorder=6)

# ── Save ───────────────────────────────────────────────────────────────────────
out = "docs/architecture_diagram.png"
plt.tight_layout(pad=0.2)
plt.savefig(out, dpi=150, bbox_inches="tight",
            facecolor=C["white"], edgecolor="none")
print(f"Saved → {out}")
