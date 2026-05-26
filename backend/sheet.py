"""Mark sheet PDF generator – "はてな展" design."""

from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import json

DATA_DIR = Path(__file__).parent.parent / "data"

# ── Font ─────────────────────────────────────────────────────────────────────
_FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUnicode", _FONT_PATH))
JP_FONT = "ArialUnicode"

# ── Page ─────────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4   # 595.28 x 841.89 pt
BG_COLOR = (0.961, 0.941, 0.890)   # cream

# ── Registration marks (must match omr.py) ────────────────────────────────────
MARK_SIZE = 10 * mm
MARK_INSET = 10 * mm

# ── Margins ───────────────────────────────────────────────────────────────────
MARGIN_LEFT  = 13 * mm
MARGIN_RIGHT = 13 * mm
MARGIN_TOP   = 10 * mm

# ── Bubble ────────────────────────────────────────────────────────────────────
BUBBLE_RADIUS = 5.5 * mm

# ── Column layout (must match omr.py) ─────────────────────────────────────────
USABLE_WIDTH = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
HALF_WIDTH   = USABLE_WIDTH / 2
HALF_ROWS    = 10

HEADER_ZONE_HEIGHT = 70 * mm   # space above first row line

ROW_HEIGHT   = 17 * mm         # height per question row
# Bubble center is shifted below row midpoint to leave room for ABCD labels
BUBBLE_Y_IN_ROW_OFFSET = 2.5 * mm

# Column x geometry
COL_NUM_OFFSET          = 10 * mm   # number label from col start
COL_FIRST_BUBBLE_OFFSET = 24 * mm   # A bubble from col start
COL_SPACING             = 16 * mm   # A→B, B→C, C→D

# Left column
LEFT_COL_START = MARGIN_LEFT
LEFT_NUM_X  = LEFT_COL_START + COL_NUM_OFFSET
LEFT_A_X    = LEFT_COL_START + COL_FIRST_BUBBLE_OFFSET
LEFT_B_X    = LEFT_A_X + COL_SPACING
LEFT_C_X    = LEFT_B_X + COL_SPACING
LEFT_D_X    = LEFT_C_X + COL_SPACING

# Right column
RIGHT_COL_START = MARGIN_LEFT + HALF_WIDTH
RIGHT_NUM_X = RIGHT_COL_START + COL_NUM_OFFSET
RIGHT_A_X   = RIGHT_COL_START + COL_FIRST_BUBBLE_OFFSET
RIGHT_B_X   = RIGHT_A_X + COL_SPACING
RIGHT_C_X   = RIGHT_B_X + COL_SPACING
RIGHT_D_X   = RIGHT_C_X + COL_SPACING

# Y reference (ReportLab bottom-left origin)
HEADERS_Y   = PAGE_H - MARGIN_TOP - HEADER_ZONE_HEIGHT   # top line of row area
ROW_START_Y = HEADERS_Y                                   # rows start at top line

# ── Exported constants for omr.py ─────────────────────────────────────────────
LEFT_COL_A_X_PT          = LEFT_A_X
RIGHT_COL_A_X_PT         = RIGHT_A_X
COL_SPACING_PT           = COL_SPACING
ROW_START_Y_PT           = ROW_START_Y
ROW_HEIGHT_PT            = ROW_HEIGHT
BUBBLE_RADIUS_PT         = BUBBLE_RADIUS
BUBBLE_Y_IN_ROW_OFFSET_PT = BUBBLE_Y_IN_ROW_OFFSET


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_registration_marks(c: canvas.Canvas) -> None:
    c.setFillColorRGB(0, 0, 0)
    positions = [
        (MARK_INSET, PAGE_H - MARK_INSET - MARK_SIZE),
        (PAGE_W - MARK_INSET - MARK_SIZE, PAGE_H - MARK_INSET - MARK_SIZE),
        (MARK_INSET, MARK_INSET),
        (PAGE_W - MARK_INSET - MARK_SIZE, MARK_INSET),
    ]
    for x, y in positions:
        c.rect(x, y, MARK_SIZE, MARK_SIZE, fill=1, stroke=0)


def _draw_bubble(c: canvas.Canvas, cx: float, cy: float) -> None:
    c.setFillColorRGB(*BG_COLOR)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.0)
    c.circle(cx, cy, BUBBLE_RADIUS, fill=1, stroke=1)


def _hline(c: canvas.Canvas, y: float, x0: float = None, x1: float = None,
           width: float = 0.5) -> None:
    if x0 is None: x0 = MARGIN_LEFT
    if x1 is None: x1 = PAGE_W - MARGIN_RIGHT
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(width)
    c.line(x0, y, x1, y)


def _draw_row(c: canvas.Canvas, i: int, q_num: int, is_right: bool) -> None:
    """Draw one question row (number + ABCD labels + bubbles)."""
    col_start = RIGHT_COL_START if is_right else LEFT_COL_START
    num_x     = RIGHT_NUM_X    if is_right else LEFT_NUM_X
    xs        = [RIGHT_A_X, RIGHT_B_X, RIGHT_C_X, RIGHT_D_X] if is_right \
                else [LEFT_A_X, LEFT_B_X, LEFT_C_X, LEFT_D_X]

    row_top_y   = ROW_START_Y - i * ROW_HEIGHT          # ReportLab top of row
    bubble_y    = row_top_y - ROW_HEIGHT/2 - BUBBLE_Y_IN_ROW_OFFSET
    label_y     = bubble_y + BUBBLE_RADIUS + 1.5 * mm   # ABCD label above bubble
    num_y       = bubble_y - 1.5 * mm                   # number centred with bubble

    # Question number (bold, zero-padded)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(num_x, num_y, f"{q_num:02d}")

    # ABCD labels
    c.setFont("Helvetica", 7)
    for label, cx in zip(["A", "B", "C", "D"], xs):
        c.drawCentredString(cx, label_y, label)

    # Bubbles
    for cx in xs:
        _draw_bubble(c, cx, bubble_y)

    # Row separator (except after last row)
    sep_y = row_top_y - ROW_HEIGHT
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.setLineWidth(0.3)
    c.line(col_start, sep_y, col_start + HALF_WIDTH - 1*mm, sep_y)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_marksheet() -> bytes:
    """Generate A4 mark sheet PDF matching the はてな展 design."""
    # Load data
    with open(DATA_DIR / "active.json", encoding="utf-8") as f:
        active_ids: list[str] = json.load(f)["active_ids"]
    with open(DATA_DIR / "questions.json", encoding="utf-8") as f:
        questions_by_id = {q["id"]: q for q in json.load(f)["questions"]}

    active_questions = [questions_by_id[qid] for qid in active_ids if qid in questions_by_id]
    n_questions = len(active_questions)
    left_count  = min(n_questions, HALF_ROWS)
    right_count = max(0, n_questions - HALF_ROWS)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("マークシート")

    # ── Background ──────────────────────────────────────────────────────────
    c.setFillColorRGB(*BG_COLOR)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── Registration marks ──────────────────────────────────────────────────
    _draw_registration_marks(c)

    # ── Header row 1: HATENA · EXHIBITION · 2026  /  はてな展 ──────────────
    c.setFillColorRGB(0, 0, 0)
    header1_y = PAGE_H - MARGIN_TOP - 12 * mm
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN_LEFT, header1_y, "HATENA  \u00b7  EXHIBITION  \u00b7  2026")
    c.setFont(JP_FONT, 8)
    c.drawRightString(PAGE_W - MARGIN_RIGHT, header1_y, "\u306f\u3066\u306a\u5c55")

    # ── Title: ？？？診断 ──────────────────────────────────────────────────
    title_y = PAGE_H - MARGIN_TOP - 42 * mm
    c.setFont(JP_FONT, 52)
    c.drawCentredString(PAGE_W / 2, title_y, "\uff1f\uff1f\uff1f\u8a3a\u65ad")

    # ── Instructions ────────────────────────────────────────────────────────
    instr1_y = PAGE_H - MARGIN_TOP - 57 * mm
    instr2_y = instr1_y - 5.5 * mm
    c.setFont(JP_FONT, 8.5)
    c.drawCentredString(PAGE_W / 2, instr1_y,
        "A\u30fbB\u30fbC\u30fbD\u306e\u3046\u3061\u3001\u3082\u3063\u3068\u3082"
        "\u8fd1\u3044\u3082\u306e\u3092\u3000\u3072\u3068\u3064\u3060\u3051\u3000"
        "\u5857\u308a\u3064\u3076\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
    c.drawCentredString(PAGE_W / 2, instr2_y,
        "\u7b54\u3048\u306f\u65e9\u304f\u3001\u8ff7\u3063\u305f\u3089\u76f4\u611f\u3067\u3002")

    # ── Top line ────────────────────────────────────────────────────────────
    _hline(c, HEADERS_Y, width=0.8)

    # ── Question rows ────────────────────────────────────────────────────────
    for i in range(left_count):
        _draw_row(c, i, i + 1, is_right=False)
    for i in range(right_count):
        _draw_row(c, i, HALF_ROWS + i + 1, is_right=True)

    # ── Bottom line ─────────────────────────────────────────────────────────
    max_rows   = max(left_count, right_count)
    bottom_y   = ROW_START_Y - max_rows * ROW_HEIGHT
    _hline(c, bottom_y, width=0.8)

    # ── Footer ──────────────────────────────────────────────────────────────
    footer_top = bottom_y - 5 * mm

    # "塗り方" section
    c.setFont(JP_FONT, 8)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(MARGIN_LEFT, footer_top - 4 * mm, "\u5857\u308a\u65b9")

    # 良い例: filled circle
    ex_y  = footer_top - 10 * mm
    ex_x  = MARGIN_LEFT + 16 * mm
    c.setFillColorRGB(0, 0, 0)
    c.circle(ex_x, ex_y, 4 * mm, fill=1, stroke=0)
    c.setFont("Helvetica", 6.5)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(ex_x, ex_y - 6 * mm, "\u25cb \u826f\u3044\u4f8b")

    # Divider
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.setLineWidth(0.4)
    c.line(ex_x + 8 * mm, footer_top - 2 * mm, ex_x + 8 * mm, footer_top - 15 * mm)

    # Bad examples
    bad_labels = ["\u00d7 \u3046\u3059\u3044", "\u00d7 \u30c1\u30a7\u30c3\u30af",
                  "\u00d7 \u30d0\u30c4", "\u00d7 \u306f\u307f\u51fa\u3057"]
    bad_circles = [
        lambda c, x, y: (c.setLineWidth(0.3), c.setFillColorRGB(0.7,0.7,0.7),
                         c.circle(x, y, 4*mm, fill=1, stroke=1)),   # うすい
        lambda c, x, y: (c.setLineWidth(1.5), c.setFillColorRGB(*BG_COLOR),
                         c.circle(x, y, 4*mm, fill=1, stroke=1),
                         c.line(x-3.5*mm, y-3.5*mm, x+3.5*mm, y+3.5*mm),
                         c.line(x+3.5*mm, y-3.5*mm, x-3.5*mm, y+3.5*mm)),  # チェック
        lambda c, x, y: (c.setLineWidth(1.5), c.setFillColorRGB(*BG_COLOR),
                         c.circle(x, y, 4*mm, fill=1, stroke=1)),   # バツ (outline only)
        lambda c, x, y: (c.setFillColorRGB(0, 0, 0),
                         c.circle(x, y+1*mm, 5*mm, fill=1, stroke=0),
                         c.setFillColorRGB(*BG_COLOR),
                         c.circle(x, y, 4*mm, fill=1, stroke=0),
                         c.setStrokeColorRGB(0,0,0), c.setLineWidth(1.0),
                         c.circle(x, y, 4*mm, fill=0, stroke=1)),   # はみ出し
    ]
    for j, (lbl, draw_fn) in enumerate(zip(bad_labels, bad_circles)):
        bx = ex_x + 16 * mm + j * 20 * mm
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(*BG_COLOR)
        draw_fn(c, bx, ex_y)
        c.setFont("Helvetica", 6.5)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(bx, ex_y - 6 * mm, lbl)

    # Instructions + ANS/20Q
    c.setFont(JP_FONT, 8)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(MARGIN_LEFT, bottom_y - 20 * mm,
        "\u8a18\u5165\u5f8c\u3001\u51fa\u53e3\u306e\u30b9\u30ad\u30e3\u30ca\u30fc"
        "\u306b\u304b\u3056\u3057\u3066\u304f\u3060\u3055\u3044")
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN_RIGHT, bottom_y - 20 * mm,
        f"ANS / {n_questions}Q")

    c.save()
    return buf.getvalue()
