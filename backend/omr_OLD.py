"""OMR (Optical Mark Recognition) engine for mark sheet scanning.

Pipeline:
1. Receive base64 JPEG image
2. Decode to numpy array -> OpenCV image
3. Grayscale conversion
4. Gaussian blur (noise removal)
5. Adaptive thresholding (handles uneven lighting)
6. Find contours -> locate 4 registration marks (solid black squares at corners)
7. Perspective transform (correct tilt/angle)
8. Divide warped image into grid based on known bubble positions
9. For each cell: calculate black pixel ratio
10. If ratio > threshold -> mark as filled
11. Return array of answers

Two-column layout (Design C):
- Left column: Q1..Q10 (rows 0..9)
- Right column: Q11..Q20 (rows 0..9)
- Answers are concatenated: left_answers + right_answers
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# ── Constants derived from sheet.py ──────────────────────────────────────────
# These mirror the ReportLab-based layout but are expressed in *points* (1pt =
# 1px at 72 dpi).  After perspective correction we warp the image to a
# canonical A4-sized pixel grid so these coordinates apply directly.

_MM = 72 / 25.4  # points-per-mm

# A5 page size
PAGE_WIDTH_PT  = 419.53
PAGE_HEIGHT_PT = 595.28

# Registration mark geometry (8mm size, 8mm inset)
MARK_SIZE_PT  = 22.68   # 8mm in points
MARK_INSET_PT = 22.68   # 8mm in points

# Canonical warped image size (A5 aspect ratio)
WARP_W = 800
WARP_H = int(round(WARP_W * PAGE_HEIGHT_PT / PAGE_WIDTH_PT))  # ~1135

# Scale factors from points -> warped pixels
_SX = WARP_W / PAGE_WIDTH_PT
_SY = WARP_H / PAGE_HEIGHT_PT

# Registration mark CENTRES in image coordinates (top-left origin).
# mark centre = MARK_INSET + MARK_SIZE/2 = 8mm + 4mm = 12mm = 34.02pt
_REG_CENTRES_IMG = {
    "tl": ( 34.02,  34.02),
    "tr": (385.51,  34.02),
    "bl": ( 34.02, 561.26),
    "br": (385.51, 561.26),
}

# ── Two-column bubble layout (matches sheet.py A5 layout) ────────────────
HALF_ROWS = 10  # questions per column

# Bubble X positions per choice (A,B,C,D) in image-coordinate points
_LEFT_COL_X_PTS  = [144.74, 160.47, 176.2, 191.93]
_RIGHT_COL_X_PTS = [344.01, 358.7, 374.43, 390.16]

# Bubble Y positions for rows 0-9 in image-coordinate points (top-left origin)
_ROW_Y_PTS = [190.1, 226.95, 263.8, 300.65, 337.5, 374.35, 411.2, 448.05, 484.9, 521.75]

# Bubble radius (3.5mm)
BUBBLE_RADIUS_PT = 9.92

_COL_LABELS = ["A", "B", "C", "D"]

# ── Bubble detection parameters ──────────────────────────────────────────────

# バブル内側のサンプリング半径倍率（0.7 = バブル半径の70%内側のみ）
# 外周アウトライン部分を除外してノイズを減らす
FILL_INNER_SCALE = 0.7

# バブル専用適応的二値化パラメータ（マーク検出より大きなblockSizeで局所照明を正規化）
BUBBLE_THRESH_BLOCK = 51
BUBBLE_THRESH_C = 10

# 行内判定パラメータ
FILL_BLANK_MAX  = 0.30   # 最大値がこれ未満 → BLANK（未回答）
FILL_DETECT_MIN = 0.35   # 最大値がこれ以上かつ差分OK → 確定
FILL_DIFF_MIN   = 0.15   # 1位と2位の差がこれ以上 → 確定（それ以下はUNCLEAR）
FILL_MULTI_MIN  = 0.40   # 2位がこれ以上 → MULTI（複数回答疑惑）

# ステータス定数
STATUS_OK      = "ok"       # 正常検出
STATUS_BLANK   = "blank"    # 未回答
STATUS_MULTI   = "multi"    # 複数回答
STATUS_UNCLEAR = "unclear"  # 判定不能

DATA_DIR = Path(__file__).parent.parent / "data"


# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class OmrResult:
    answers: list[Optional[str]]   # e.g. ["A", "C", None, "B", ...]
    question_count: int
    error: Optional[str] = None
    statuses: list[str] = field(default_factory=list)  # STATUS_* per question
    number_answers: dict = field(default_factory=dict)  # {"q001": 17, ...}
    number_answers: dict = field(default_factory=dict)  # {"q001": 17, ...}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_question_count() -> int:
    """Return number of active questions from data/active.json."""
    with open(DATA_DIR / "active.json", encoding="utf-8") as f:
        data = json.load(f)
    return len(data["active_ids"])


def _decode_image(image_base64: str) -> np.ndarray:
    """Decode a base64-encoded JPEG/PNG to an OpenCV BGR image."""
    raw = base64.b64decode(image_base64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("画像をデコードできませんでした。JPEG/PNG形式の画像を送信してください。")
    return img


def _preprocess(img: np.ndarray) -> np.ndarray:
    """Convert to greyscale, blur, and adaptive-threshold.
    Handles both dark-background (white marks) and light-background (colored marks).
    """
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 画像が暗背景かどうか判定（平均輝度が低ければ暗背景）
    mean_val = cv2.mean(grey)[0]
    if mean_val < 128:
        # 暗背景（黒地に白■）: そのまま二値化（白い部分が検出される）
        blurred = cv2.GaussianBlur(grey, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=8,
        )
    else:
        # 明背景（白地にピンク■など）: 反転して二値化
        blurred = cv2.GaussianBlur(grey, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=8,
        )
    return thresh


def _preprocess_bubbles(img: np.ndarray) -> np.ndarray:
    """Adaptive threshold tuned for bubble fill detection.

    Uses a larger block size than _preprocess so local lighting variations
    (shadows, uneven illumination) are normalised within each bubble's
    neighbourhood rather than across registration-mark-sized regions.
    """
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grey, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=BUBBLE_THRESH_BLOCK,
        C=BUBBLE_THRESH_C,
    )
    return thresh


def _find_registration_marks(
    thresh: np.ndarray,
    img_h: int,
    img_w: int,
) -> Optional[np.ndarray]:
    """Detect 4 registration mark centres.  Returns a 4x2 float32 array
    ordered [TL, TR, BL, BR] or None if detection failed.
    """
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Expected mark area relative to image area.
    page_area = img_h * img_w
    mark_frac = (MARK_SIZE_PT * MARK_SIZE_PT) / (PAGE_WIDTH_PT * PAGE_HEIGHT_PT)
    min_area = page_area * mark_frac * 0.05
    max_area = page_area * mark_frac * 5.0

    candidates: list[tuple[float, float, float, float]] = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h if h > 0 else 0
        if aspect < 0.5 or aspect > 2.0:
            continue
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            continue
        solidity = area / hull_area
        if solidity < 0.5:
            continue
        cx = x + w / 2.0
        cy = y + h / 2.0
        candidates.append((cx, cy, w, h))

    if len(candidates) < 4:
        return None

    mid_x = img_w / 2.0
    mid_y = img_h / 2.0

    tl_cands = [(cx, cy) for cx, cy, _, _ in candidates if cx < mid_x and cy < mid_y]
    tr_cands = [(cx, cy) for cx, cy, _, _ in candidates if cx >= mid_x and cy < mid_y]
    bl_cands = [(cx, cy) for cx, cy, _, _ in candidates if cx < mid_x and cy >= mid_y]
    br_cands = [(cx, cy) for cx, cy, _, _ in candidates if cx >= mid_x and cy >= mid_y]

    if not (tl_cands and tr_cands and bl_cands and br_cands):
        return None

    def _closest_to_corner(cands: list, corner_x: float, corner_y: float):
        return min(cands, key=lambda c: (c[0] - corner_x) ** 2 + (c[1] - corner_y) ** 2)

    tl = _closest_to_corner(tl_cands, 0, 0)
    tr = _closest_to_corner(tr_cands, img_w, 0)
    bl = _closest_to_corner(bl_cands, 0, img_h)
    br = _closest_to_corner(br_cands, img_w, img_h)

    return np.array([tl, tr, bl, br], dtype=np.float32)


def _perspective_warp(
    img: np.ndarray,
    marks: np.ndarray,
) -> np.ndarray:
    """Warp the image so the registration mark centres map to their canonical
    positions in the WARP_W x WARP_H pixel grid.
    """
    dst = np.array([
        [_REG_CENTRES_IMG["tl"][0] * _SX, _REG_CENTRES_IMG["tl"][1] * _SY],
        [_REG_CENTRES_IMG["tr"][0] * _SX, _REG_CENTRES_IMG["tr"][1] * _SY],
        [_REG_CENTRES_IMG["bl"][0] * _SX, _REG_CENTRES_IMG["bl"][1] * _SY],
        [_REG_CENTRES_IMG["br"][0] * _SX, _REG_CENTRES_IMG["br"][1] * _SY],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(marks, dst)
    warped = cv2.warpPerspective(img, M, (WARP_W, WARP_H))
    return warped


def _judge_row(ratios: list[float]) -> tuple[Optional[str], str]:
    """Determine the selected answer and status from 4-choice fill ratios.

    Returns (answer_label_or_None, status_string).
    """
    sorted_cols = sorted(range(4), key=lambda i: ratios[i], reverse=True)
    best_col    = sorted_cols[0]
    best_ratio  = ratios[best_col]
    second_ratio = ratios[sorted_cols[1]]

    if best_ratio < FILL_BLANK_MAX:
        return None, STATUS_BLANK

    if best_ratio >= FILL_DETECT_MIN and (best_ratio - second_ratio) >= FILL_DIFF_MIN:
        return _COL_LABELS[best_col], STATUS_OK

    if second_ratio >= FILL_MULTI_MIN:
        return None, STATUS_MULTI

    return None, STATUS_UNCLEAR


def _bubble_centre_px(row_idx: int, col_idx: int, is_right: bool = False) -> tuple[int, int]:
    """Return (x, y) in warped-pixel space for a bubble.

    row_idx: 0-based row within the column (0..9)
    col_idx: 0=A, 1=B, 2=C, 3=D
    is_right: True for right column (Q11-Q20), False for left (Q1-Q10)
    """
    col_x_pts = _RIGHT_COL_X_PTS if is_right else _LEFT_COL_X_PTS
    img_x = col_x_pts[col_idx]
    img_y = _ROW_Y_PTS[row_idx]
    px = int(round(img_x * _SX))
    py = int(round(img_y * _SY))
    return px, py


def _read_column_bubbles(
    thresh_warped: np.ndarray,
    n_rows: int,
    is_right: bool,
) -> list[tuple[Optional[str], str]]:
    """Read filled bubbles for one column.  Returns list of (answer, status)."""
    avg_scale = (_SX + _SY) / 2
    r = int(round(BUBBLE_RADIUS_PT * avg_scale * FILL_INNER_SCALE))

    results: list[tuple[Optional[str], str]] = []

    for row in range(n_rows):
        ratios = [0.0] * 4

        for c in range(4):
            cx, cy = _bubble_centre_px(row, c, is_right=is_right)
            y1 = max(cy - r, 0)
            y2 = min(cy + r, thresh_warped.shape[0])
            x1 = max(cx - r, 0)
            x2 = min(cx + r, thresh_warped.shape[1])
            roi = thresh_warped[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            mask = np.zeros_like(roi, dtype=np.uint8)
            mr = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
            cv2.circle(mask, (roi.shape[1] // 2, roi.shape[0] // 2), mr, 255, -1)
            masked = cv2.bitwise_and(roi, mask)
            total_pixels = cv2.countNonZero(mask)
            if total_pixels == 0:
                continue
            ratios[c] = cv2.countNonZero(masked) / total_pixels

        results.append(_judge_row(ratios))

    return results


def _read_bubbles(
    thresh_warped: np.ndarray,
    n_questions: int,
) -> tuple[list[Optional[str]], list[str]]:
    """Read filled bubbles from the thresholded warped image.

    Returns (answers, statuses) for all n_questions.
    Two-column layout: left Q1..Q10, right Q11..Q20.
    """
    left_count  = min(n_questions, HALF_ROWS)
    right_count = max(0, n_questions - HALF_ROWS)

    left_pairs  = _read_column_bubbles(thresh_warped, left_count,  is_right=False)
    right_pairs = _read_column_bubbles(thresh_warped, right_count, is_right=True)

    all_pairs = left_pairs + right_pairs
    answers  = [p[0] for p in all_pairs]
    statuses = [p[1] for p in all_pairs]
    return answers, statuses


def _read_number_fields(warped: np.ndarray, n_questions: int) -> dict:
    """数字記入エリアをOCRで読み取り、問いIDと数値のdictを返す。"""
    result = {}
    avg_scale = (_SX + _SY) / 2

    for qid, field in NUMBER_FIELDS.items():
        row = field["row"]
        is_right = field["is_right"]

        # A列バブルの中心座標を基準にする
        cx, cy = _bubble_centre_px(row, 0, is_right=is_right)

        # 記入欄のROI
        x1 = max(cx + NUMBER_BOX_DX, 0)
        y1 = max(cy + NUMBER_BOX_DY, 0)
        x2 = min(x1 + NUMBER_BOX_W, warped.shape[1])
        y2 = min(y1 + NUMBER_BOX_H, warped.shape[0])

        roi = warped[y1:y2, x1:x2]
        if roi.size == 0:
            continue

        # OCR前処理：グレースケール→リサイズ→二値化
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        scale = 4
        enlarged = cv2.resize(gray, (roi.shape[1] * scale, roi.shape[0] * scale),
                              interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(enlarged, 150, 255,
                                  cv2.THRESH_BINARY)

        # Tesseractで数字のみ認識
        pil_img = Image.fromarray(binary)
        text = pytesseract.image_to_string(
            pil_img,
            config='--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'
        ).strip()

        # 1〜30の範囲にクランプ
        try:
            n = int(text)
            if 1 <= n <= 30:
                result[qid] = n
        except ValueError:
            pass  # 読み取り失敗はスキップ

    return result


# ── Public API ───────────────────────────────────────────────────────────────


# 数字記入欄の設定（warped画像座標）
# Q17-20: 右列のバブル位置の左側にある大きなボックス
_NUMBER_BOX = {
    'q024': {'y1': 754, 'y2': 799, 'x1': 665, 'x2': 775},  # Q17 カフェ 1-9
    'q003': {'y1': 824, 'y2': 869, 'x1': 665, 'x2': 775},  # Q18 バス 1-20
    'q001': {'y1': 894, 'y2': 939, 'x1': 665, 'x2': 775},  # Q19 ロッカー 1-12
    'q002': {'y1': 964, 'y2': 1009, 'x1': 665, 'x2': 775},  # Q20 オフィス 1-9
}
def debug_image(image_base64: str) -> dict:
    """Process image and return annotated debug JPEG (base64) + diagnostics."""
    img = _decode_image(image_base64)
    img_h, img_w = img.shape[:2]
    debug = img.copy()

    thresh = _preprocess(img)
    marks = _find_registration_marks(thresh, img_h, img_w)

    info: dict = {
        "image_size": [img_w, img_h],
        "marks_found": marks is not None,
        "marks": None,
        "answers": [],
        "bubble_ratios": [],
        "error": None,
    }

    if marks is None:
        info["error"] = "基準マーク未検出"
        # 二値化画像をそのまま返す（何が見えているか確認用）
        thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        _, buf = cv2.imencode(".jpg", thresh_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        info["debug_image"] = base64.b64encode(buf.tobytes()).decode("ascii")
        return info

    info["marks"] = marks.tolist()

    # 検出マークを緑丸で描画
    for (cx, cy) in marks:
        cv2.circle(debug, (int(cx), int(cy)), 20, (0, 255, 0), 3)

    # パース補正
    warped = _perspective_warp(img, marks)
    thresh_warped = _preprocess_bubbles(warped)
    n_questions = _load_question_count()

    avg_scale = (_SX + _SY) / 2
    r = int(round(BUBBLE_RADIUS_PT * avg_scale * FILL_INNER_SCALE))

    # BGR色定義
    _STATUS_COLOR = {
        STATUS_OK:      (0, 220, 0),    # 緑: 正常検出
        STATUS_BLANK:   (80, 80, 80),   # グレー: 未回答
        STATUS_MULTI:   (0, 0, 220),    # 赤: 複数回答
        STATUS_UNCLEAR: (0, 140, 255),  # オレンジ: 判定不能
    }

    ratios_all = []
    row_results = []

    for is_right in [False, True]:
        n_rows = min(n_questions, HALF_ROWS) if not is_right else max(0, n_questions - HALF_ROWS)
        for row in range(n_rows):
            row_ratios = [0.0] * 4
            for c in range(4):
                cx, cy = _bubble_centre_px(row, c, is_right=is_right)
                y1, y2 = max(cy - r, 0), min(cy + r, thresh_warped.shape[0])
                x1, x2 = max(cx - r, 0), min(cx + r, thresh_warped.shape[1])
                roi = thresh_warped[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                mask = np.zeros_like(roi, dtype=np.uint8)
                mr = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
                cv2.circle(mask, (roi.shape[1] // 2, roi.shape[0] // 2), mr, 255, -1)
                masked = cv2.bitwise_and(roi, mask)
                total = cv2.countNonZero(mask)
                row_ratios[c] = cv2.countNonZero(masked) / total if total > 0 else 0.0

            ratios_all.append([round(v, 3) for v in row_ratios])
            answer, status = _judge_row(row_ratios)
            row_results.append(status)

            # 色分け描画
            status_color = _STATUS_COLOR.get(status, (80, 80, 80))
            sorted_cols = sorted(range(4), key=lambda i: row_ratios[i], reverse=True)
            best_c = sorted_cols[0]
            for c in range(4):
                cx, cy = _bubble_centre_px(row, c, is_right=is_right)
                ratio = row_ratios[c]
                circle_color = status_color if (c == best_c and status == STATUS_OK) else (80, 80, 80)
                cv2.circle(warped, (cx, cy), r, circle_color, 2)
                # 赤い中心点（座標確認用）
                cv2.circle(warped, (cx, cy), 3, (0, 0, 255), -1)
                cv2.putText(warped, f"{ratio:.2f}",
                            (cx - r, cy - r - 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, circle_color, 1)

    answers, statuses = _read_bubbles(thresh_warped, n_questions)
    info["bubble_ratios"] = ratios_all
    info["row_results"] = row_results
    info["answers"]  = answers
    info["statuses"] = statuses

    # warped画像をエンコード
    _, buf = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 85])
    info["debug_image"] = base64.b64encode(buf.tobytes()).decode("ascii")
    return info


def process_image(image_base64: str) -> OmrResult:
    """Process a base64 JPEG image and return detected answers."""
    # Decode
    img = _decode_image(image_base64)
    img_h, img_w = img.shape[:2]

    # Preprocess
    thresh = _preprocess(img)

    # Find registration marks
    marks = _find_registration_marks(thresh, img_h, img_w)
    if marks is None:
        # フォールバック: 画像全体をA5として処理
        import numpy as np
        marks = np.array([
            [img_w * 0.05, img_h * 0.05],
            [img_w * 0.95, img_h * 0.05],
            [img_w * 0.05, img_h * 0.95],
            [img_w * 0.95, img_h * 0.95],
        ], dtype=np.float32)

    # Perspective warp
    warped = _perspective_warp(img, marks)

    # Threshold the warped image (bubble-specific parameters)
    thresh_warped = _preprocess_bubbles(warped)

    # Load question count
    n_questions = _load_question_count()

    # Read bubbles
    answers, statuses = _read_bubbles(thresh_warped, n_questions)

    # 数字記入欄のOCR
    import pytesseract
    from PIL import Image as PILImage
    number_answers = {}
    
    # active_idsからnumber問題を特定
    try:
        with open(DATA_DIR / 'active.json', encoding='utf-8') as f:
            active_ids = json.load(f)['active_ids']
        with open(DATA_DIR / 'questions.json', encoding='utf-8') as f:
            questions = {q['id']: q for q in json.load(f)['questions']}
        
        for i, qid in enumerate(active_ids):
            q = questions.get(qid, {})
            if q.get('input_type') != 'number':
                continue
            if qid not in _NUMBER_BOX:
                continue
            
            box = _NUMBER_BOX[qid]
            y1 = box['y1']
            y2 = min(box['y2'], warped.shape[0])
            x1, x2 = box['x1'], box['x2']
            
            roi = warped[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            # 枠線除外: 内側8pxをトリミング
            roi = roi[5:-5, 5:-5]
            if roi.size == 0:
                continue
            
            b, g, r = cv2.split(roi)
            pink_mask = (r.astype(int) - b.astype(int) > 30)
            clean = roi.copy()
            clean[pink_mask] = [255, 255, 255]
            gray = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY)
            _, binary_inv = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            text = ''
            roi_area = gray.shape[0] * gray.shape[1]
            # 二値化→erosionで枠線と数字を分離→輪郭で数字領域を取得
            _, bin_inv = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            eroded = cv2.erode(bin_inv, kernel, iterations=2)
            contours2, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            text = ''
            if contours2:
                areas2 = [(cv2.contourArea(c), c) for c in contours2 if cv2.contourArea(c) > 30]
                if areas2:
                    c2 = max(areas2, key=lambda x: x[0])[1]
                    bx2, by2, bw2, bh2 = cv2.boundingRect(c2)
                    digit2 = gray[by2:by2+bh2, bx2:bx2+bw2]
                    padded2 = cv2.copyMakeBorder(digit2, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
                    enlarged2 = cv2.resize(padded2, (padded2.shape[1]*4, padded2.shape[0]*4), interpolation=cv2.INTER_CUBIC)
                    _, bin2 = cv2.threshold(enlarged2, 150, 255, cv2.THRESH_BINARY)
                    text = pytesseract.image_to_string(
                        PILImage.fromarray(bin2),
                        config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789'
                    ).strip()
            
            try:
                n = int(text)
                nr = q.get('number_range', [1, 30])
                if nr[0] <= n <= nr[1]:
                    number_answers[qid] = n
                    answers[i] = str(n)
                else:
                    default = (nr[0] + nr[1]) // 2
                    number_answers[qid] = default
                    answers[i] = str(default)
            except ValueError:
                nr = q.get('number_range', [1, 30])
                default = (nr[0] + nr[1]) // 2
                number_answers[qid] = default
                answers[i] = str(default)
    except Exception:
        pass

    return OmrResult(answers=answers, question_count=n_questions, statuses=statuses, number_answers=number_answers)
