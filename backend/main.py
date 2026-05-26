"""
展示会マークシート診断システム — FastAPI エントリーポイント。

エンドポイント:
  GET  /health                  ヘルスチェック
  GET  /api/active              現在有効な問いと選択肢を返す
  POST /api/submit              回答を保存・スコア計算 → result_id を返す
  GET  /api/result/{result_id}  診断結果の取得
  GET  /api/results             結果一覧（管理用）
  GET  /api/sheet/pdf           マークシートPDFを生成・ダウンロード
  POST /api/scan                画像スキャン → 回答・ステータス返却（保存なし）
  POST /api/debug/scan          デバッグ用：アノテーション画像 + バブル充填率
  POST /api/print/{result_id}   結果ページを印刷（Chrome headless + lpr）

実行: .venv/bin/uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import omr
import printer
import scoring
import sheet


# ---------------------------------------------------------------------------
# Lifespan: 起動時に DB 初期化
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    scoring.init_db()
    yield


app = FastAPI(
    title="展示会マークシート診断システム",
    description="20問のマークシートからの16タイプ診断 API",
    version="0.2.0",
    lifespan=lifespan,
)

# 開発中は CORS を緩めに（ngrok や別ホストからのアクセスを許容）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------

class SubmitRequest(BaseModel):
    answers: List[Optional[str]] = Field(
        ..., description='20要素の回答配列。例: ["A", "B", null, "C", ...]'
    )


class SubmitResponse(BaseModel):
    result_id: str


class ScanRequest(BaseModel):
    image: str = Field(..., description="base64エンコードされたJPEG/PNG。data:image/...; のプレフィックス込みでもOK")


class ScanResponse(BaseModel):
    answers: List[Optional[str]]
    statuses: List[str]
    question_count: int
    error: Optional[str] = None


class DebugScanResponse(BaseModel):
    answers: List[Optional[str]]
    statuses: List[str]
    question_count: int
    fill_ratios: List[List[float]] = []
    annotated_image_base64: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 基本エンドポイント
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/active")
def get_active_questions() -> dict:
    """有効な問いの一覧（回答UI/結果ページで使う想定）。"""
    questions = scoring.load_active_questions()
    return {
        "question_count": len(questions),
        "questions": [
            {
                "id": q["id"],
                "text": q["text"],
                "summary": q.get("summary", q["text"]),
                "options": q["options"],
            }
            for q in questions
        ],
    }


# ---------------------------------------------------------------------------
# 回答送信・結果取得
# ---------------------------------------------------------------------------

@app.post("/api/submit", response_model=SubmitResponse)
def submit(req: SubmitRequest) -> SubmitResponse:
    """回答を保存・スコア計算 → result_id を返す。"""
    expected_n = len(scoring.load_active_ids())
    if len(req.answers) != expected_n:
        raise HTTPException(
            status_code=400,
            detail=f"answers の長さが不正です（期待 {expected_n}, 実際 {len(req.answers)}）",
        )
    for i, ans in enumerate(req.answers):
        if ans is not None and ans not in ("A", "B", "C", "D"):
            raise HTTPException(
                status_code=400,
                detail=f"answers[{i}] が不正な値です: {ans!r}",
            )
    try:
        result_id = scoring.submit_answers(req.answers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return SubmitResponse(result_id=result_id)


@app.get("/api/result/{result_id}")
def get_result(result_id: str) -> dict:
    result = scoring.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="result_id が見つかりません")
    return result


@app.get("/api/results")
def list_results(limit: int = 100) -> dict:
    return {"results": scoring.list_results(limit=limit)}


# ---------------------------------------------------------------------------
# マークシートPDF
# ---------------------------------------------------------------------------

@app.get("/api/sheet/pdf")
def get_sheet_pdf() -> Response:
    """マークシートPDFを生成して返す（ブラウザで開く/印刷用）。"""
    try:
        pdf_bytes = sheet.generate_sheet_pdf()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF生成失敗: {e}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="hatena_marksheet.pdf"',
        },
    )


# ---------------------------------------------------------------------------
# OMR
# ---------------------------------------------------------------------------

def _strip_data_url_prefix(image: str) -> str:
    """data:image/...;base64, プレフィックスを除去して生base64を返す。"""
    if "," in image:
        return image.split(",", 1)[1]
    return image


@app.post("/api/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    """画像から回答配列を読み取る（保存しない）。"""
    question_count = len(scoring.load_active_ids())
    try:
        result = omr.process_image(_strip_data_url_prefix(req.image))
    except Exception as e:
        return ScanResponse(
            answers=[None] * question_count,
            statuses=["unclear"] * question_count,
            question_count=question_count,
            error=str(e),
        )
    if result.error:
        return ScanResponse(
            answers=[None] * question_count,
            statuses=["unclear"] * question_count,
            question_count=question_count,
            error=result.error,
        )
    return ScanResponse(
        answers=result.answers,
        statuses=result.statuses,
        question_count=result.question_count,
    )


@app.post("/api/debug/scan")
def debug_scan(req: ScanRequest) -> dict:
    """デバッグ用：透視補正後の画像＋バブル充填率を返す。"""
    try:
        return omr.debug_image(_strip_data_url_prefix(req.image))
    except Exception as e:
        return {"error": str(e), "marks_found": False, "answers": [], "bubble_ratios": []}


# ---------------------------------------------------------------------------
# 印刷
# ---------------------------------------------------------------------------

@app.post("/api/print/{result_id}")
def print_result(result_id: str) -> dict:
    """結果ページを Chrome headless で PDF 化 → lpr で印刷キューに送る。"""
    if scoring.get_result(result_id) is None:
        raise HTTPException(status_code=404, detail="result_id が見つかりません")
    try:
        result = printer.print_result(result_id)
        return result if isinstance(result, dict) else {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
