"""Synthetic test for the OMR engine (two-column layout).

Generates a white A4 canvas with:
- 4 solid black registration marks at the canonical positions
- Filled circles at known answer positions (left and/or right column)
Then encodes it as base64 JPEG and runs process_image().
"""

from __future__ import annotations

import base64
import sys
from unittest.mock import patch

import cv2
import numpy as np

from omr import (
    MARK_SIZE_PT,
    PAGE_HEIGHT_PT,
    PAGE_WIDTH_PT,
    BUBBLE_RADIUS_PT,
    _LEFT_COL_X_PTS,
    _RIGHT_COL_X_PTS,
    _ROW_Y_PTS,
    _REG_CENTRES_IMG,
    HALF_ROWS,
    process_image,
)

# Use a resolution that approximates a phone camera photo of an A4 sheet
# (roughly 2x the 72-dpi point size).
SCALE = 2.0
IMG_W = int(round(PAGE_WIDTH_PT * SCALE))
IMG_H = int(round(PAGE_HEIGHT_PT * SCALE))


def _pt_to_px(x_pt: float, y_pt_img: float) -> tuple[int, int]:
    """Convert point coords (image top-left origin) to pixel coords."""
    return int(round(x_pt * SCALE)), int(round(y_pt_img * SCALE))


def _draw_registration_marks(img: np.ndarray) -> None:
    """Draw the 4 registration marks as solid black rectangles."""
    half = MARK_SIZE_PT / 2
    for corner in ("tl", "tr", "bl", "br"):
        cx_pt, cy_pt = _REG_CENTRES_IMG[corner]
        x1, y1 = _pt_to_px(cx_pt - half, cy_pt - half)
        x2, y2 = _pt_to_px(cx_pt + half, cy_pt + half)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)


def _bubble_img_coords(question_idx: int, col_idx: int, n_questions: int) -> tuple[float, float]:
    """Return (x_pt, y_img_pt) in image-top-left-origin points for a bubble.

    question_idx: 0-based global question number
    col_idx: 0=A, 1=B, 2=C, 3=D
    n_questions: total number of questions (determines column split)
    """
    left_count = min(n_questions, HALF_ROWS)

    if question_idx < left_count:
        col_x_pts = _LEFT_COL_X_PTS
        row = question_idx
    else:
        col_x_pts = _RIGHT_COL_X_PTS
        row = question_idx - HALF_ROWS

    img_x_pt = col_x_pts[col_idx]
    img_y_pt = _ROW_Y_PTS[row]
    return img_x_pt, img_y_pt


def _fill_bubble(img: np.ndarray, question_idx: int, col_idx: int, n_questions: int) -> None:
    """Fill a bubble at the given question/column with solid black."""
    img_x_pt, img_y_pt = _bubble_img_coords(question_idx, col_idx, n_questions)
    cx, cy = _pt_to_px(img_x_pt, img_y_pt)
    r = int(round(BUBBLE_RADIUS_PT * SCALE))
    cv2.circle(img, (cx, cy), r, (0, 0, 0), -1)


def _draw_unfilled_bubble(img: np.ndarray, question_idx: int, col_idx: int, n_questions: int) -> None:
    """Draw an unfilled bubble outline (as on the real sheet)."""
    img_x_pt, img_y_pt = _bubble_img_coords(question_idx, col_idx, n_questions)
    cx, cy = _pt_to_px(img_x_pt, img_y_pt)
    r = int(round(BUBBLE_RADIUS_PT * SCALE))
    cv2.circle(img, (cx, cy), r, (0, 0, 0), 2)


def generate_test_image(
    answers: dict[int, int],
    n_questions: int = 5,
) -> np.ndarray:
    """Create a synthetic mark sheet image.

    Args:
        answers: mapping of question_idx (0-based) -> col_idx (0=A .. 3=D)
        n_questions: number of questions to draw

    Returns:
        BGR image as numpy array
    """
    img = np.ones((IMG_H, IMG_W, 3), dtype=np.uint8) * 255  # white canvas
    _draw_registration_marks(img)

    # Draw all bubble outlines, then fill the selected ones
    for q in range(n_questions):
        for c in range(4):
            _draw_unfilled_bubble(img, q, c, n_questions)

    for q_idx, c_idx in answers.items():
        _fill_bubble(img, q_idx, c_idx, n_questions)

    return img


def image_to_base64(img: np.ndarray) -> str:
    """Encode an OpenCV image to base64 JPEG string."""
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return base64.b64encode(buf.tobytes()).decode("ascii")


def run_tests() -> bool:
    """Run OMR tests and return True if all passed."""
    all_passed = True

    # ── Test 1: 5 questions (left column only) with known answers ────────
    print("=" * 60)
    print("Test 1: 5 questions (left column only) with known answers")
    print("=" * 60)

    # Q1=A(0), Q2=C(2), Q3=B(1), Q4=D(3), Q5=A(0)
    expected_answers = {0: 0, 1: 2, 2: 1, 3: 3, 4: 0}
    expected_labels = ["A", "C", "B", "D", "A"]

    img = generate_test_image(expected_answers, n_questions=5)
    b64 = image_to_base64(img)
    result = process_image(b64)

    print(f"  Question count: {result.question_count}")
    print(f"  Error: {result.error}")
    print(f"  Expected: {expected_labels}")
    print(f"  Detected: {result.answers}")

    if result.error:
        print("  FAIL: OMR returned an error")
        all_passed = False
    elif result.answers[:len(expected_labels)] == expected_labels:
        print("  PASS")
    else:
        print("  FAIL: answers do not match")
        all_passed = False
        for i, (exp, det) in enumerate(zip(expected_labels, result.answers)):
            status = "OK" if exp == det else "MISMATCH"
            print(f"    Q{i+1}: expected={exp}, detected={det} [{status}]")

    # ── Test 2: partial answers (left column only) ───────────────────────
    print()
    print("=" * 60)
    print("Test 2: partial answers (Q1=B, Q3=D, others blank)")
    print("=" * 60)

    partial_answers = {0: 1, 2: 3}  # Q1=B, Q3=D
    expected_labels_2 = ["B", None, "D", None, None]

    img2 = generate_test_image(partial_answers, n_questions=5)
    b64_2 = image_to_base64(img2)
    result2 = process_image(b64_2)

    print(f"  Question count: {result2.question_count}")
    print(f"  Error: {result2.error}")
    print(f"  Expected: {expected_labels_2}")
    print(f"  Detected: {result2.answers}")

    if result2.error:
        print("  FAIL: OMR returned an error")
        all_passed = False
    elif result2.answers[:len(expected_labels_2)] == expected_labels_2:
        print("  PASS")
    else:
        print("  FAIL: answers do not match")
        all_passed = False
        for i, (exp, det) in enumerate(zip(expected_labels_2, result2.answers)):
            status = "OK" if exp == det else "MISMATCH"
            print(f"    Q{i+1}: expected={exp}, detected={det} [{status}]")

    # ── Test 3: rotated image (~5 degrees) ───────────────────────────────
    print()
    print("=" * 60)
    print("Test 3: slightly rotated image (~5 degrees)")
    print("=" * 60)

    img3_base = generate_test_image({0: 2, 1: 0, 2: 3, 3: 1, 4: 2}, n_questions=5)
    expected_labels_3 = ["C", "A", "D", "B", "C"]

    pad = 150
    padded = cv2.copyMakeBorder(
        img3_base, pad, pad, pad, pad,
        cv2.BORDER_CONSTANT, value=(255, 255, 255),
    )
    ph, pw = padded.shape[:2]
    centre = (pw // 2, ph // 2)
    M_rot = cv2.getRotationMatrix2D(centre, 5, 1.0)
    img3_rot = cv2.warpAffine(
        padded, M_rot, (pw, ph),
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    b64_3 = image_to_base64(img3_rot)
    result3 = process_image(b64_3)

    print(f"  Question count: {result3.question_count}")
    print(f"  Error: {result3.error}")
    print(f"  Expected: {expected_labels_3}")
    print(f"  Detected: {result3.answers}")

    if result3.error:
        print("  FAIL: OMR returned an error")
        all_passed = False
    elif result3.answers[:len(expected_labels_3)] == expected_labels_3:
        print("  PASS")
    else:
        print("  FAIL: answers do not match")
        all_passed = False
        for i, (exp, det) in enumerate(zip(expected_labels_3, result3.answers)):
            status = "OK" if exp == det else "MISMATCH"
            print(f"    Q{i+1}: expected={exp}, detected={det} [{status}]")

    # ── Test 4: 20 questions (both columns) ──────────────────────────────
    print()
    print("=" * 60)
    print("Test 4: 20 questions (both columns) with known answers")
    print("=" * 60)

    # Answers for all 20 questions: alternating pattern
    # Q1=A, Q2=B, Q3=C, Q4=D, Q5=A, Q6=B, Q7=C, Q8=D, Q9=A, Q10=B
    # Q11=C, Q12=D, Q13=A, Q14=B, Q15=C, Q16=D, Q17=A, Q18=B, Q19=C, Q20=D
    answers_20 = {}
    expected_labels_20 = []
    for i in range(20):
        col = i % 4
        answers_20[i] = col
        expected_labels_20.append(_label_for_col(col))

    img4 = generate_test_image(answers_20, n_questions=20)
    b64_4 = image_to_base64(img4)
    with patch("omr._load_question_count", return_value=20):
        result4 = process_image(b64_4)

    print(f"  Question count: {result4.question_count}")
    print(f"  Error: {result4.error}")
    print(f"  Expected: {expected_labels_20}")
    print(f"  Detected: {result4.answers}")

    if result4.error:
        print("  FAIL: OMR returned an error")
        all_passed = False
    elif result4.answers == expected_labels_20:
        print("  PASS")
    else:
        print("  FAIL: answers do not match")
        all_passed = False
        for i, (exp, det) in enumerate(zip(expected_labels_20, result4.answers)):
            status = "OK" if exp == det else "MISMATCH"
            if status == "MISMATCH":
                print(f"    Q{i+1}: expected={exp}, detected={det} [{status}]")

    # ── Test 5: 20 questions with rotation ───────────────────────────────
    print()
    print("=" * 60)
    print("Test 5: 20 questions, rotated ~5 degrees")
    print("=" * 60)

    # Q1=D, Q5=A, Q10=C, Q11=B, Q15=D, Q20=A, rest blank
    sparse_answers = {0: 3, 4: 0, 9: 2, 10: 1, 14: 3, 19: 0}
    expected_labels_5 = [None] * 20
    expected_labels_5[0] = "D"
    expected_labels_5[4] = "A"
    expected_labels_5[9] = "C"
    expected_labels_5[10] = "B"
    expected_labels_5[14] = "D"
    expected_labels_5[19] = "A"

    img5_base = generate_test_image(sparse_answers, n_questions=20)
    pad5 = 150
    padded5 = cv2.copyMakeBorder(
        img5_base, pad5, pad5, pad5, pad5,
        cv2.BORDER_CONSTANT, value=(255, 255, 255),
    )
    ph5, pw5 = padded5.shape[:2]
    centre5 = (pw5 // 2, ph5 // 2)
    M_rot5 = cv2.getRotationMatrix2D(centre5, 5, 1.0)
    img5_rot = cv2.warpAffine(
        padded5, M_rot5, (pw5, ph5),
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    b64_5 = image_to_base64(img5_rot)
    with patch("omr._load_question_count", return_value=20):
        result5 = process_image(b64_5)

    print(f"  Question count: {result5.question_count}")
    print(f"  Error: {result5.error}")
    print(f"  Expected: {expected_labels_5}")
    print(f"  Detected: {result5.answers}")

    if result5.error:
        print("  FAIL: OMR returned an error")
        all_passed = False
    elif result5.answers == expected_labels_5:
        print("  PASS")
    else:
        print("  FAIL: answers do not match")
        all_passed = False
        for i, (exp, det) in enumerate(zip(expected_labels_5, result5.answers)):
            status = "OK" if exp == det else "MISMATCH"
            if status == "MISMATCH":
                print(f"    Q{i+1}: expected={exp}, detected={det} [{status}]")

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


def _label_for_col(col: int) -> str:
    return ["A", "B", "C", "D"][col]


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
