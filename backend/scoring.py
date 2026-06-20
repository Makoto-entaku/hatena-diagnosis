"""
スコアリング・タイプ判定・SQLite永続化。

16タイプ診断ロジック:
- 主軸4軸（社交/寛容/行動/自分大切）× 各5問 × ±1.5/±0.5/-0.5/-1.5
- 副軸1軸（ロジカル軸）× 5問 — レーダー5本目用、タイプ判定には使わない
- 正規化: (raw + offset) / span * 100 → 0〜100
- 二値化: > threshold(50) → 正側、≤ threshold → 負側
- 4軸の二値化結果（E/I, W/N, A/L, S/O）を連結して4文字コード → 16タイプ判定
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# プロジェクトルートからの相対パス
_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE_DIR / "data"
_QUESTIONS_PATH = _DATA_DIR / "questions.json"
_ACTIVE_PATH = _DATA_DIR / "active.json"
_TYPES_PATH = _DATA_DIR / "types.json"

# DBファイルのパス。環境変数 RESULTS_DB_PATH で上書き可能。
DB_PATH = Path(os.environ.get("RESULTS_DB_PATH", str(_DATA_DIR / "results.db")))


# ---------------------------------------------------------------------------
# データ読み込み
# ---------------------------------------------------------------------------

def load_questions() -> Dict[str, dict]:
    """questions.json を読み込み、id をキーとする dict を返す。"""
    with open(_QUESTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {q["id"]: q for q in data["questions"]}


def load_active_ids() -> List[str]:
    """active.json から有効な問いIDの順序リストを返す。"""
    with open(_ACTIVE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("active_ids", data.get("active_questions", [])))


def load_types_config() -> dict:
    """types.json をそのまま返す。"""
    with open(_TYPES_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_active_questions() -> List[dict]:
    """active.json の順番で問い情報のリストを返す。"""
    questions = load_questions()
    return [questions[qid] for qid in load_active_ids()]


# ---------------------------------------------------------------------------
# スコア計算
# ---------------------------------------------------------------------------

def number_to_zone(n: int, number_range: list = None) -> str:
    """数字をlow/mid/highゾーンに変換する。
    number_rangeが指定された場合はそのrangeを3等分して相対判定する。
    """
    if number_range is None:
        if n <= 10: return 'low'
        elif n <= 20: return 'mid'
        else: return 'high'
    lo, hi = number_range[0], number_range[1]
    span = hi - lo + 1
    third = span / 3
    pos = n - lo
    if pos < third: return 'low'
    elif pos < third * 2: return 'mid'
    else: return 'high'


def compute_raw_scores(answers: List[Optional[str]]) -> Dict[str, float]:
    """
    回答配列を軸ごとの生スコアに集計する。

    answers: 各問の回答 ["A", "B", null, "D", ...]
              長さは active_ids と同じ。null は未回答（スキップ）。
    """
    active_questions = load_active_questions()
    if len(answers) != len(active_questions):
        raise ValueError(
            f"answers長さ不一致: {len(answers)} != {len(active_questions)}"
        )

    raw: Dict[str, float] = {}
    for question, ans in zip(active_questions, answers):
        if ans is None:
            continue
        if question.get("input_type") == "number":
            # 数字記入問題：数値をゾーンに変換してスコアを取得
            try:
                n = int(ans)
                nr = question.get("number_range")
                zone = number_to_zone(n, nr)
                delta = question["scoring"].get(zone, {})
            except (ValueError, TypeError):
                continue
        else:
            delta = question["scoring"].get(ans, {})
        for axis, value in delta.items():
            raw[axis] = raw.get(axis, 0.0) + float(value)
    return raw


def normalize_score(
    raw: float, max_per_question: float, num_questions: int
) -> float:
    """
    生スコアを 0〜100 のレーダー値に変換する。

    正規化式: (raw + offset) / span * 100
      offset = max_per_question * num_questions   (例: 1.5 × 5 = 7.5)
      span   = max_per_question * num_questions * 2 (例: 15)
    """
    offset = max_per_question * num_questions
    span = offset * 2
    if span <= 0:
        return 0.0
    value = (raw + offset) / span * 100.0
    return max(0.0, min(100.0, value))


def compute_normalized_scores(answers: List[Optional[str]]) -> Dict[str, float]:
    """各軸（主軸+副軸）の 0〜100 正規化スコアを返す。"""
    config = load_types_config()
    raw = compute_raw_scores(answers)

    cfg = config["scoring_config"]
    main_max = float(cfg["max_per_question"])
    main_n = int(cfg["questions_per_axis"])

    normalized: Dict[str, float] = {}

    for axis in config["axes"]:
        axis_id = axis["id"]
        normalized[axis_id] = normalize_score(
            raw.get(axis_id, 0.0), main_max, main_n
        )

    for sub_axis in config.get("sub_axes", []):
        axis_id = sub_axis["id"]
        sub_max = float(sub_axis.get("max_per_question", main_max))
        sub_n = int(sub_axis.get("questions_per_axis", main_n))
        normalized[axis_id] = normalize_score(
            raw.get(axis_id, 0.0), sub_max, sub_n
        )

    return normalized


def determine_type_code(normalized_scores: Dict[str, float]) -> str:
    """正規化スコアから4文字タイプコード (例: EWAS) を求める。"""
    config = load_types_config()
    threshold = float(config["scoring_config"]["binary_threshold"])
    code_chars: List[str] = []

    for axis in config["axes"]:
        score = normalized_scores.get(axis["id"], 50.0)
        if score > threshold:
            code_chars.append(axis["code_positive"])
        else:
            code_chars.append(axis["code_negative"])

    return "".join(code_chars)


def find_type_by_code(code: str) -> Optional[dict]:
    """typesからコード一致するタイプを返す。なければ None。"""
    config = load_types_config()
    for t in config["types"]:
        if t["code"] == code:
            return t
    return None


def determine_type(normalized_scores: Dict[str, float]) -> dict:
    """正規化スコアからタイプ情報を決定する。"""
    code = determine_type_code(normalized_scores)
    type_info = find_type_by_code(code)
    if type_info is None:
        config = load_types_config()
        default_code = config.get("default_type_code", "")
        type_info = find_type_by_code(default_code)
    if type_info is None:
        raise RuntimeError(f"タイプ判定失敗: code={code}")
    return type_info


def compute_display_scores(
    normalized_scores: Dict[str, float],
) -> Dict[str, float]:
    """表示用スコア（行動軸を「怠惰度」として逆転表示する処理込み）。"""
    config = load_types_config()
    display: Dict[str, float] = {}
    for axis in config["axes"]:
        score = normalized_scores.get(axis["id"], 50.0)
        if axis.get("invert_display"):
            score = 100.0 - score
        display[axis["display_name"]] = round(score, 1)
    for sub_axis in config.get("sub_axes", []):
        score = normalized_scores.get(sub_axis["id"], 50.0)
        display[sub_axis["display_name"]] = round(score, 1)
    return display


# ---------------------------------------------------------------------------
# SQLite 永続化
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """results テーブルを作成する（存在しなければ）。"""
    _ensure_data_dir()
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id             TEXT PRIMARY KEY,
                created_at     TEXT NOT NULL,
                answers        TEXT NOT NULL,
                scores         TEXT NOT NULL,
                type_id        TEXT NOT NULL,
                number_answers TEXT
            )
            """
        )
        # 既存DBへのカラム追加（初回のみ実行される）
        try:
            con.execute("ALTER TABLE results ADD COLUMN number_answers TEXT")
        except sqlite3.OperationalError:
            pass  # すでにカラムがある場合はスキップ
        con.commit()
    finally:
        con.close()


def save_result(
    answers: List[Optional[str]],
    normalized_scores: Dict[str, float],
    type_code: str,
    number_answers: Optional[Dict[str, int]] = None,
) -> str:
    """結果を保存し、result_id (UUIDv4文字列) を返す。"""
    init_db()
    result_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            "INSERT INTO results (id, created_at, answers, scores, type_id, number_answers) VALUES (?, ?, ?, ?, ?, ?)",
            (
                result_id,
                created_at,
                json.dumps(answers, ensure_ascii=False),
                json.dumps(normalized_scores, ensure_ascii=False),
                type_code,
                json.dumps(number_answers, ensure_ascii=False) if number_answers else None,
            ),
        )
        con.commit()
    finally:
        con.close()
    return result_id


def _fetch_answer_distributions() -> Dict[str, Dict[str, float]]:
    """全回答から各問の選択肢比率を計算する。{q_idx: {answer: ratio}}"""
    init_db()
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute("SELECT answers FROM results").fetchall()
    finally:
        con.close()
    if not rows:
        return {}

    counts: Dict[int, Dict[str, int]] = {}
    totals: Dict[int, int] = {}

    for (answers_json,) in rows:
        answers = json.loads(answers_json)
        for i, ans in enumerate(answers):
            if ans is None:
                continue
            counts.setdefault(i, {})
            counts[i][ans] = counts[i].get(ans, 0) + 1
            totals[i] = totals.get(i, 0) + 1

    result = {}
    for i, ans_counts in counts.items():
        total = totals[i]
        result[i] = {ans: count / total for ans, count in ans_counts.items()}
    return result


def _fetch_answer_distributions() -> Dict[str, Dict[str, float]]:
    """全回答から各問の選択肢比率を計算する。{q_idx: {answer: ratio}}"""
    init_db()
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute("SELECT answers FROM results").fetchall()
    finally:
        con.close()
    if not rows:
        return {}

    counts: Dict[int, Dict[str, int]] = {}
    totals: Dict[int, int] = {}

    for (answers_json,) in rows:
        answers = json.loads(answers_json)
        for i, ans in enumerate(answers):
            if ans is None:
                continue
            counts.setdefault(i, {})
            counts[i][ans] = counts[i].get(ans, 0) + 1
            totals[i] = totals.get(i, 0) + 1

    result = {}
    for i, ans_counts in counts.items():
        total = totals[i]
        result[i] = {ans: count / total for ans, count in ans_counts.items()}
    return result


def _fetch_axis_means() -> Dict[str, float]:
    """全結果から各軸の平均値を計算する。1件もなければ {}."""
    init_db()
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute("SELECT scores FROM results").fetchall()
    finally:
        con.close()
    if not rows:
        return {}
    sums: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for (scores_json,) in rows:
        scores = json.loads(scores_json)
        for axis, value in scores.items():
            sums[axis] = sums.get(axis, 0.0) + float(value)
            counts[axis] = counts.get(axis, 0) + 1
    return {axis: sums[axis] / counts[axis] for axis in sums}


def get_result(result_id: str) -> Optional[dict]:
    """result_id から完全な結果データを返す。なければ None。"""
    init_db()
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute(
            "SELECT id, created_at, answers, scores, type_id FROM results WHERE id = ?",
            (result_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None

    rid, created_at, answers_json, scores_json, type_code = row
    raw_answers = json.loads(answers_json)
    normalized_scores = json.loads(scores_json)

    type_info = find_type_by_code(type_code) or {}

    means = _fetch_axis_means()
    axis_comparisons: Dict[str, float] = {}
    for axis, value in normalized_scores.items():
        mean = means.get(axis, value)
        axis_comparisons[axis] = round(value - mean, 1)

    questions = load_active_questions()

    # ちょっと変だった回答（少数派TOP3）
    distributions = _fetch_answer_distributions()
    weird_answers = []
    for i, ans in enumerate(raw_answers):
        # null（読み取れなかった問い）は除外
        if ans is None:
            continue
        dist = distributions.get(i, {})
        ratio = dist.get(ans, 1.0)
        if ratio < 0.3 and i < len(questions):
            q = questions[i]
            options = q.get("options", {})
            # 数字記入問題は「〇番」という形式で表示
            if q.get("input_type") == "number":
                answer_label = f"{ans}番"
            elif isinstance(options, dict):
                answer_label = options.get(ans, ans)
            else:
                answer_label = ans
            weird_answers.append({
                "question_summary": q["text"],
                "answer": ans,
                "answer_label": answer_label,
                "ratio": round(ratio * 100),
            })

    weird_answers.sort(key=lambda x: x["ratio"])
    weird_answers = weird_answers[:3]

    return {
        "result_id": rid,
        "created_at": created_at,
        "type_code": type_code,
        "type_id": type_info.get("id", ""),
        "type_name": type_info.get("name", ""),
        "tagline": type_info.get("tagline", ""),
        "description": type_info.get("description", ""),
        "tendency": type_info.get("tendency", ""),
        "advice": type_info.get("advice", ""),
        "suited": type_info.get("suited", ""),
        "strength": type_info.get("strength", ""),
        "scores": {k: round(v, 1) for k, v in normalized_scores.items()},
        "display_scores": compute_display_scores(normalized_scores),
        "raw_answers": raw_answers,
        "questions": [
            {
                "id": q["id"],
                "text": q["text"],
                "summary": q["text"],
                "options": q["options"],
            }
            for q in questions
        ],
        "axis_comparisons": axis_comparisons,
        "weird_answers": weird_answers,
    }


# ---------------------------------------------------------------------------
# 統合エントリーポイント
# ---------------------------------------------------------------------------

def submit_answers(
    answers: List[Optional[str]],
    number_answers: Optional[Dict[str, int]] = None,
) -> str:
    """回答を受け取り、スコア計算・タイプ判定・保存をして result_id を返す。"""
    normalized_scores = compute_normalized_scores(answers)
    type_code = determine_type_code(normalized_scores)
    return save_result(answers, normalized_scores, type_code, number_answers)


def list_results(limit: int = 100) -> List[dict]:
    """結果一覧（管理用）。新しい順。"""
    init_db()
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT id, created_at, type_id FROM results ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        con.close()
    return [
        {"id": r[0], "created_at": r[1], "type_id": r[2]} for r in rows
    ]
