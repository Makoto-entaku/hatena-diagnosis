"""Mark sheet PDF generator – A5 size."""

from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import json

DATA_DIR = Path(__file__).parent.parent / "data"

_FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUnicode", _FONT_PATH))
JP_FONT = "ArialUnicode"

PAGE_W, PAGE_H = A5
BG_COLOR = (1.0, 1.0, 1.0)

MARK_SIZE  = 8 * mm
MARK_INSET = 8 * mm

MARGIN_LEFT  = 10 * mm
MARGIN_RIGHT = 10 * mm
MARGIN_TOP   =  8 * mm

BUBBLE_RADIUS = 1.75 * mm

USABLE_WIDTH = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
HALF_WIDTH   = USABLE_WIDTH / 2
HALF_ROWS    = 10

HEADER_ZONE_HEIGHT     = 42 * mm
ROW_HEIGHT             = 13 * mm
BUBBLE_Y_IN_ROW_OFFSET =  1.5 * mm

COL_NUM_OFFSET          = 8  * mm
COL_FIRST_BUBBLE_OFFSET = 16 * mm
COL_SPACING             = 12 * mm

LEFT_COL_START = MARGIN_LEFT
LEFT_NUM_X  = LEFT_COL_START + COL_NUM_OFFSET
LEFT_A_X    = LEFT_COL_START + COL_FIRST_BUBBLE_OFFSET
LEFT_B_X    = LEFT_A_X + COL_SPACING
LEFT_C_X    = LEFT_B_X + COL_SPACING
LEFT_D_X    = LEFT_C_X + COL_SPACING

RIGHT_COL_START = MARGIN_LEFT + HALF_WIDTH
RIGHT_NUM_X = RIGHT_COL_START + COL_NUM_OFFSET
RIGHT_A_X   = RIGHT_COL_START + COL_FIRST_BUBBLE_OFFSET
RIGHT_B_X   = RIGHT_A_X + COL_SPACING
RIGHT_C_X   = RIGHT_B_X + COL_SPACING
RIGHT_D_X   = RIGHT_C_X + COL_SPACING

HEADERS_Y   = PAGE_H - MARGIN_TOP - HEADER_ZONE_HEIGHT
ROW_START_Y = HEADERS_Y

NUMBER_INPUT_Q_NUMS = {1, 2, 4}


def _draw_registration_marks(c):
    c.setFillColorRGB(0, 0, 0)
    positions = [
        (MARK_INSET, PAGE_H - MARK_INSET - MARK_SIZE),
        (PAGE_W - MARK_INSET - MARK_SIZE, PAGE_H - MARK_INSET - MARK_SIZE),
        (MARK_INSET, MARK_INSET),
        (PAGE_W - MARK_INSET - MARK_SIZE, MARK_INSET),
    ]
    for x, y in positions:
        c.rect(x, y, MARK_SIZE, MARK_SIZE, fill=1, stroke=0)


def _draw_bubble(c, cx, cy):
    c.setFillColorRGB(*BG_COLOR)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.8)
    c.circle(cx, cy, BUBBLE_RADIUS, fill=1, stroke=1)


def _hline(c, y, x0=None, x1=None, width=0.5):
    if x0 is None: x0 = MARGIN_LEFT
    if x1 is None: x1 = PAGE_W - MARGIN_RIGHT
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(width)
    c.line(x0, y, x1, y)


def _draw_row(c, i, q_num, is_right):
    col_start = RIGHT_COL_START if is_right else LEFT_COL_START
    num_x     = RIGHT_NUM_X    if is_right else LEFT_NUM_X
    xs        = [RIGHT_A_X, RIGHT_B_X, RIGHT_C_X, RIGHT_D_X] if is_right \
                else [LEFT_A_X, LEFT_B_X, LEFT_C_X, LEFT_D_X]

    row_top_y = ROW_START_Y - i * ROW_HEIGHT
    bubble_y  = row_top_y - ROW_HEIGHT / 2 - BUBBLE_Y_IN_ROW_OFFSET
    label_y   = bubble_y + BUBBLE_RADIUS + 1.2 * mm
    num_y     = bubble_y - 1.2 * mm

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(num_x, num_y, f"{q_num:02d}")

    if q_num in NUMBER_INPUT_Q_NUMS:
        # 2桁数字記入ボックス（小さめ）
        box_w = 14 * mm
        box_h = 8 * mm
        box_x = num_x + 4 * mm
        box_y = bubble_y - box_h / 2
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(1, 1, 1)
        c.setLineWidth(0.8)
        c.rect(box_x, box_y, box_w, box_h, fill=1, stroke=1)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.setFont("Helvetica", 5.5)
        c.drawCentredString(box_x + box_w / 2, box_y + box_h + 1 * mm, "No.")
    else:
        c.setFont("Helvetica", 6)
        for label, cx in zip(["A", "B", "C", "D"], xs):
            c.drawCentredString(cx, label_y, label)
        for cx in xs:
            _draw_bubble(c, cx, bubble_y)

    sep_y = row_top_y - ROW_HEIGHT
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.setLineWidth(0.3)
    c.line(col_start, sep_y, col_start + HALF_WIDTH - 1 * mm, sep_y)


def generate_marksheet():
    with open(DATA_DIR / "active.json", encoding="utf-8") as f:
        active_ids = json.load(f)["active_ids"]
    with open(DATA_DIR / "questions.json", encoding="utf-8") as f:
        questions_by_id = {q["id"]: q for q in json.load(f)["questions"]}

    active_questions = [questions_by_id[qid] for qid in active_ids if qid in questions_by_id]
    n_questions = len(active_questions)
    left_count  = min(n_questions, HALF_ROWS)
    right_count = max(0, n_questions - HALF_ROWS)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    c.setTitle("マークシート")

    c.setFillColorRGB(*BG_COLOR)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    _draw_registration_marks(c)

    c.setFillColorRGB(0, 0, 0)
    header1_y = PAGE_H - MARGIN_TOP - 10 * mm
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN_LEFT, header1_y, "HATENA  \u00b7  EXHIBITION  \u00b7  2026")
    c.setFont(JP_FONT, 7)
    c.drawRightString(PAGE_W - MARGIN_RIGHT, header1_y, "\u306f\u3066\u306a\u5c55")

    title_y = PAGE_H - MARGIN_TOP - 30 * mm
    c.setFont(JP_FONT, 36)
    c.drawCentredString(PAGE_W / 2, title_y, "\uff1f\uff1f\uff1f\u8a3a\u65ad")

    instr_y = PAGE_H - MARGIN_TOP - 38 * mm
    c.setFont(JP_FONT, 7)
    c.drawCentredString(PAGE_W / 2, instr_y,
        "A\u30fbB\u30fbC\u30fbD\u306e\u3046\u3061\u3001\u3082\u3063\u3068\u3082\u8fd1\u3044\u3082\u306e\u3092\u3000\u3072\u3068\u3064\u3060\u3051\u3000\u5857\u308a\u3064\u3076\u3057\u3066\u304f\u3060\u3055\u3044\u3002")

    _hline(c, HEADERS_Y, width=0.8)

    for i in range(left_count):
        _draw_row(c, i, i + 1, is_right=False)
    for i in range(right_count):
        _draw_row(c, i, HALF_ROWS + i + 1, is_right=True)

    max_rows = max(left_count, right_count)
    bottom_y = ROW_START_Y - max_rows * ROW_HEIGHT
    _hline(c, bottom_y, width=0.8)

    footer_y = bottom_y - 6 * mm
    c.setFont(JP_FONT, 7)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(MARGIN_LEFT, footer_y,
        "\u8a18\u5165\u5f8c\u3001\u51fa\u53e3\u306e\u30b9\u30ad\u30e3\u30ca\u30fc\u306b\u304b\u3056\u3057\u3066\u304f\u3060\u3055\u3044")
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN_RIGHT, footer_y, f"ANS / {n_questions}Q")

    c.save()
    return buf.getvalue()
