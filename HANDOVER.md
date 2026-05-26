# 展示会マークシート診断システム — 引き継ぎドキュメント

> **対象読者**: このシステムを初めて触る開発者。前任者の作業履歴や環境前提を知らない状態から、理解・改修・拡張できるようになることを目的としています。

---

## 目次

1. [システム概要](#1-システム概要)
2. [ユーザー体験の流れ](#2-ユーザー体験の流れ)
3. [技術スタック・動作環境](#3-技術スタック動作環境)
4. [ディレクトリ構成](#4-ディレクトリ構成)
5. [環境構築（ゼロから）](#5-環境構築ゼロから)
6. [起動手順](#6-起動手順)
7. [スマホからのアクセス（本番運用）](#7-スマホからのアクセス本番運用)
8. [APIエンドポイント一覧](#8-apiエンドポイント一覧)
9. [フロントエンド画面構成](#9-フロントエンド画面構成)
10. [OMRエンジン詳解](#10-omrエンジン詳解)
11. [データ形式仕様](#11-データ形式仕様)
12. [スコアリング・タイプ判定ロジック](#12-スコアリングタイプ判定ロジック)
13. [印刷プロセス](#13-印刷プロセス)
14. [よくあるトラブル](#14-よくあるトラブル)
15. [機能拡張ガイド](#15-機能拡張ガイド)

---

## 1. システム概要

**はてな展**（仮称）という展示会イベントのための、紙マークシート診断システムです。

### 目的
来場者が展示会場で20問のA/B/C/D4択問題に回答し、出口のMac端末でシートをカメラ撮影・自動読み取りして、個別の「タイプ診断」結果をリアルタイム表示・印刷します。

### 運用フロー
```
入場
  ↓ マークシートを受け取る（A4印刷済）
展示を見ながら A/B/C/D をボールペンで塗りつぶす
  ↓
出口のMac端末（スマホ）でシートをカメラ撮影
  ↓ OMR（光学マーク認識）で自動読み取り
回答確認・手動修正画面で間違いがあれば直す
  ↓
「確定して診断する」ボタン
  ↓
診断結果ページ（タイプ名・スコア・相性・回答一覧）を表示
  ↓
「印刷する」ボタンで A4 印刷
```

### 動作環境
Macローカルのみ（インターネット不要）。Next.js（:3000）と FastAPI（:8000）を同一マシンで起動します。スマホからアクセスする場合は ngrok でHTTPSトンネルを使います（カメラAPIにHTTPSが必要なため）。

---

## 2. ユーザー体験の流れ

| ステップ | URL | 担当コンポーネント |
|---------|-----|------------------|
| カメラ起動・撮影 | `/scan` | `CameraView.tsx` |
| 読み取り中（ローディング） | `/scan` | `scan/page.tsx` |
| 回答確認・手動修正 | `/scan` | `ReviewScreen`（`scan/page.tsx`内） |
| 診断結果表示 | `/result/[id]` | `ResultCard.tsx` |
| 印刷ボタン | `/result/[id]` | `PrintButton`（`ResultCard.tsx`内） |
| デバッグ（開発用） | `/debug` | `debug/page.tsx` |

---

## 3. 技術スタック・動作環境

| 役割 | 技術 | バージョン |
|------|------|----------|
| フロントエンド | Next.js 14（App Router） | 14.2.35 |
| スタイリング | Tailwind CSS | 3.x |
| バックエンド | Python FastAPI | 0.110.0 |
| OMR処理 | OpenCV-Python | 4.9.0.80 |
| 画像処理 | NumPy | 1.26.4 |
| PDF生成 | ReportLab | 4.1.0 |
| データ保存 | SQLite（標準ライブラリ） | — |
| Python | 3.9.6 | Python 3.9以上 |
| Node.js | 25.x | 18以上推奨 |
| OS | macOS | M1/M2/Intel Mac |

**フォント依存**: `sheet.py`（PDF生成）が `/Library/Fonts/Arial Unicode.ttf` を参照しています。macOS標準には含まれないケースがあります。存在しない場合はパスを変更するか別のUnicodeフォントに差し替えてください。

**プリンター**: `lpr -P EPSON_SC_PX1V` にハードコードされています。別のプリンターを使う場合は `backend/printer.py:59` の `-P` 引数を変更してください。接続済みプリンター名の確認は `lpstat -p` で。

---

## 4. ディレクトリ構成

```
exhibition-diagnostic/
├── HANDOVER.md              ← このファイル
├── README.md                ← 最小限の起動手順
├── .gitignore
│
├── backend/                 ← Python FastAPI
│   ├── main.py              ← APIエンドポイント定義
│   ├── omr.py               ← OMRエンジン（核心）
│   ├── scoring.py           ← スコア計算・タイプ判定・DB操作
│   ├── sheet.py             ← マークシートPDF生成
│   ├── printer.py           ← Chrome headless → lpr 印刷
│   ├── test_omr.py          ← OMR合成画像テスト（5ケース）
│   ├── test_scoring.py      ← スコアリングテスト
│   ├── validate_data.py     ← data/*.json の整合性チェック
│   ├── requirements.txt
│   └── .venv/               ← 仮想環境（gitignore済み）
│
├── frontend/                ← Next.js 14
│   ├── app/
│   │   ├── layout.tsx       ← ルートレイアウト
│   │   ├── page.tsx         ← トップ（/scan へリダイレクト）
│   │   ├── scan/
│   │   │   └── page.tsx     ← カメラ撮影・確認・修正UI
│   │   ├── result/
│   │   │   └── [id]/
│   │   │       ├── page.tsx     ← 診断結果ページ（SSR）
│   │   │       └── not-found.tsx
│   │   └── debug/
│   │       └── page.tsx     ← OMRデバッグ画面（開発用）
│   ├── components/
│   │   ├── CameraView.tsx   ← getUserMedia + 撮影
│   │   └── ResultCard.tsx   ← 診断結果インフォグラフィック + 印刷ボタン
│   ├── next.config.mjs      ← /api/* → localhost:8000 リバースプロキシ
│   └── ...
│
└── data/                    ← 実行時データ（gitignore推奨外）
    ├── questions.json       ← 問いバンク（現在20問）
    ├── active.json          ← 有効な問いのID一覧（20問）
    ├── types.json           ← タイプ定義・スコア軸の最大値
    └── results.db           ← SQLite（診断結果の永続化）
```

---

## 5. 環境構築（ゼロから）

### バックエンド

```bash
cd exhibition-diagnostic/backend

# Python 仮想環境を作成
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 依存ライブラリをインストール
pip install -r requirements.txt
```

> **注意**: `opencv-python` のインストールに時間がかかります（数分）。

### フロントエンド

```bash
cd exhibition-diagnostic/frontend
npm install
```

### データの確認

```bash
cd exhibition-diagnostic/backend
.venv/bin/python3 validate_data.py
```

エラーが出なければデータ整合性OK。

---

## 6. 起動手順

**ターミナルを2つ開いて並行起動します。**

```bash
# ターミナル①: バックエンド
cd exhibition-diagnostic/backend
.venv/bin/uvicorn main:app --reload --port 8000
```

```bash
# ターミナル②: フロントエンド
cd exhibition-diagnostic/frontend
npm run dev
```

| サービス | URL |
|---------|-----|
| フロントエンド | http://localhost:3000 |
| バックエンドAPI | http://localhost:8000 |
| APIドキュメント（Swagger） | http://localhost:8000/docs |
| マークシートPDF | http://localhost:8000/api/sheet/pdf |

> フロントエンドの `/api/*` リクエストは `next.config.mjs` のrewriteルールでバックエンドへ転送されるため、フロント側からのAPIはすべて `/api/...` の相対パスで統一されています。

---

## 7. スマホからのアクセス（本番運用）

スマホのカメラAPIは **HTTPS必須**のため、ngrokを使います。

```bash
# ターミナル③: ngrok（フロントのみトンネルすればOK）
ngrok http 3000
```

表示される `https://xxxx.ngrok-free.app` を控えて、スマホで `https://xxxx.ngrok-free.app/scan` を開く。

**なぜフロントだけでよいか**: `next.config.mjs` のrewriteがサーバー側で処理されるため、スマホ → ngrok(3000) → Next.js → FastAPI(8000) と内部転送されます。バックエンドを別途公開する必要はありません。

**ngrok初回設定**:
```bash
# ngrok.com で無料アカウント作成後
ngrok config add-authtoken <your-token>
```

---

## 8. APIエンドポイント一覧

すべて `http://localhost:8000` がベースURL。

| メソッド | パス | 役割 |
|---------|-----|------|
| GET | `/health` | ヘルスチェック |
| GET | `/api/sheet/pdf` | マークシートPDFを生成・ダウンロード |
| POST | `/api/scan` | 画像スキャン → 回答・ステータス返却（保存なし） |
| POST | `/api/submit` | 回答を保存・スコア計算 → result_id を返す |
| GET | `/api/result/{result_id}` | 診断結果の取得 |
| POST | `/api/print/{result_id}` | 結果ページを印刷（Chrome headless + lpr） |
| POST | `/api/debug/scan` | デバッグ用：アノテーション画像 + バブル充填率 |

### `/api/scan` リクエスト/レスポンス

```json
// リクエスト
{ "image": "<base64エンコードされたJPEG/PNG>" }

// レスポンス
{
  "answers": ["A", null, "C", "B", ...],   // 20要素、未検出はnull
  "statuses": ["ok", "blank", "multi", "unclear", ...],  // 各問の検出状態
  "question_count": 20
}
```

ステータス値の意味:
- `ok`: 正常に1択検出
- `blank`: 未回答（塗りなし）
- `multi`: 複数回答の疑い
- `unclear`: どれか塗られているが確定できない

### `/api/submit` リクエスト/レスポンス

```json
// リクエスト
{ "answers": ["A", null, "C", "B", ...] }  // 手動修正済みの20問回答

// レスポンス
{ "result_id": "uuid-v4-文字列" }
```

### `/api/result/{id}` レスポンス

```json
{
  "result_id": "...",
  "type_id": "explorer",
  "type_name": "静かに燃える探求者タイプ",
  "description": "...",
  "one_liner": "...",
  "good_match": ["...", "..."],
  "bad_match": ["..."],
  "footer_question": "...",
  "scores": { "independence": 72, "social": 35, "curiosity": 80, "action": 45 },
  "raw_answers": ["A", null, "C", ...],
  "questions": [{ "id": "q001", "text": "...", "summary": "...", "options": {...} }, ...],
  "axis_comparisons": { "independence": 14, "social": -8, "curiosity": 22, "action": -3 }
}
```

---

## 9. フロントエンド画面構成

### `/scan` — 撮影・確認画面

**状態機械**: `idle → loading → review → submitting → (redirect to /result/[id])`

- **idle**: カメラ起動ボタンを表示。`CameraView.tsx` が `getUserMedia` でカメラを取得。
- **loading**: 撮影後、`/api/scan` へPOST中。スピナー表示。
- **review**: `ReviewScreen` コンポーネントを表示。
  - 2列グリッド（左Q1〜10、右Q11〜20）
  - 各問にステータスドット（緑/グレー/赤/オレンジ）
  - A/B/C/Dボタン（同じボタンを再タップで選択解除）
  - 要確認・未回答カウントのバッジ
- **submitting**: `/api/submit` へPOST中。スピナー表示。

### `/result/[id]` — 診断結果ページ

サーバーサイドレンダリング（SSR）。`/api/result/{id}` から直接取得。

`ResultCard.tsx` のセクション構成:
1. **ヘッダー**: タイプ名・サブタイトル（紺背景）
2. **タイプセクション**: タイプ名・説明文
3. **スコアバー**: 4軸それぞれの棒グラフ + ラベル
4. **全来場者比較**: axis_comparisons を±差分で表示
5. **相性・苦手**: good_match / bad_match リスト
6. **20問の回答一覧**: Q番号・問いの要約・選択肢バッジ（2列）
7. **ひとこと診断**: one_liner（紺背景）
8. **フッター**: footer_question
9. **印刷ボタン**: `POST /api/print/{id}` を叩くボタン（印刷紙面には出ない）

`@media print` CSS: A4縦、10mmマージン。印刷ボタン非表示。

### `/debug` — OMRデバッグ画面

開発・調整用。カメラで撮影後 `/api/debug/scan` を叩き、以下を表示:
- 透視補正後の画像（バブル中心に赤点、検出色の輪郭）
- 各バブルの充填率（A:0.xx B:0.xx C:0.xx D:0.xx）
- 検出回答の一覧

---

## 10. OMRエンジン詳解

`backend/omr.py` が核心です。実際のマークシートPDF（`はてな展 — マークシート.pdf`）をPyMuPDFで解析し、座標をハードコードしています。

### 処理パイプライン

```
1. base64デコード → OpenCV BGR画像
2. グレースケール → GaussianBlur → adaptiveThreshold（blockSize=15）
3. 輪郭検出 → 4隅の黒い正方形（基準マーク）を特定
4. 透視変換（getPerspectiveTransform）で A4相当（800×1130px）に正規化
5. 変換後画像に adaptiveThreshold（blockSize=51）を適用（バブル用）
6. 各バブルの中心座標を計算 → 内側70%の円でマスキング → 黒画素率を計測
7. 各行(問)について4択の充填率を比較 → answer + status を判定
8. 全20問の answers[], statuses[] を返却
```

### 座標系の重要な注意点

座標はすべて**実際のPDFをPyMuPDFで計測した実測値**をハードコードしています（計算式ではありません）。`sheet.py` の定数値とは**異なります**（sheet.pyが生成するPDFとは別のPDFが配布されていた経緯があります）。

```python
# ページサイズ
PAGE_WIDTH_PT  = 595.0   # A4幅
PAGE_HEIGHT_PT = 842.0   # A4高さ

# 基準マーク（4隅の黒い正方形）の中心座標（画像座標系：左上原点）
_REG_CENTRES_IMG = {
    "tl": ( 51.79,  51.79),   # 左上
    "tr": (544.46,  51.79),   # 右上
    "bl": ( 51.79, 779.71),   # 左下
    "br": (544.46, 779.71),   # 右下
}
MARK_SIZE_PT = 32.18  # マーク一辺のサイズ（pt）

# バブルX座標（画像座標系、pt）
_LEFT_COL_X_PTS  = [122.22, 166.56, 211.60, 256.65]   # 左列 A,B,C,D
_RIGHT_COL_X_PTS = [365.34, 410.39, 455.44, 499.77]   # 右列 A,B,C,D

# バブルY座標（行0〜9、画像座標系、pt）
_ROW_Y_PTS = [262.37, 305.28, 348.18, 391.08, 433.98,
              476.89, 519.79, 562.69, 606.31, 649.21]

# バブル半径（pt）
BUBBLE_RADIUS_PT = 6.97
```

**座標系の統一**: `sheet.py`（ReportLab）は左下原点、`omr.py` は左上原点で統一しています。

### 基準マーク検出

`_find_registration_marks()`:
- 全輪郭を取得し、面積・アスペクト比（0.5〜2.0）・solidity（0.7以上）でフィルタ
- 画像中央を境に4象限に分類 → 各象限で最もコーナーに近いものを選択
- 失敗時: `OmrResult(error="...")`

### バブル充填率と判定

`FILL_INNER_SCALE = 0.7`: バブル外周を除いた内側70%の半径でサンプリング（外周の印刷ノイズを除去）

```python
FILL_BLANK_MAX  = 0.30   # 全選択肢の最大充填率がこれ未満 → BLANK
FILL_DETECT_MIN = 0.35   # 1位がこれ以上かつ
FILL_DIFF_MIN   = 0.15   # 1位-2位の差がこれ以上 → OK（確定）
FILL_MULTI_MIN  = 0.40   # 2位がこれ以上 → MULTI（複数疑い）
# 上記いずれでもない → UNCLEAR
```

### テスト

```bash
cd backend
.venv/bin/python3 test_omr.py
```

合成画像（NumPyで生成）を使った5ケースのテスト:
1. 5問・左列のみ・全問回答
2. 5問・部分回答（空欄あり）
3. 5問・5度傾き
4. 20問・両列・全問回答
5. 20問・スパース回答・5度傾き

---

## 11. データ形式仕様

### `data/questions.json`

```json
{
  "questions": [
    {
      "id": "q001",
      "text": "ひとりでいられる時間は、あなたにとってどのくらい大切ですか？",
      "summary": "ひとりの時間",       // 結果ページの回答一覧で使用（短い表示用）
      "options": {
        "A": "絶対に必要。ないと消耗する",
        "B": "あったほうが気持ちよく過ごせる",
        "C": "どちらでも気にならない",
        "D": "むしろひとりだと寂しい"
      },
      "scoring": {
        "A": { "independence": 3, "social": -1, "curiosity": 1, "action": -1 },
        "B": { "independence": 2 },
        "C": { "social": 1, "action": 1 },
        "D": { "independence": -1, "social": 3, "action": 1 }
      }
    }
  ]
}
```

現在20問。スコアの軸は `independence / social / curiosity / action` の4軸。スコア値は整数（負も可）。

### `data/active.json`

```json
{
  "active_ids": ["q001", "q002", ..., "q020"],  // 有効な問いのIDを順番に指定
  "updated_at": "2026-04-27"
}
```

**変更方法**: このファイルを書き換えるだけで使用する問いを入れ替えられます。問いの順序がシートの行順に直結します（`q001`→Q1, `q002`→Q2...）。変更後はシートPDFを再生成してください（`GET /api/sheet/pdf`）。

### `data/types.json`

```json
{
  "axis_max": {
    "independence": 51,
    "social": 58,
    "curiosity": 46,
    "action": 48
  },
  "default_type": "balanced",
  "types": [
    {
      "id": "explorer",
      "name": "静かに燃える探求者タイプ",
      "description": "（本文）",
      "one_liner": "（一言）",
      "good_match": ["...", "..."],
      "bad_match": ["..."],
      "footer_question": "（締めの問い）",
      "condition": { "curiosity": ">60", "social": "<50" }
    },
    {
      "id": "balanced",
      "name": "しなやかな万能型タイプ",
      // condition なし → デフォルトタイプ
    }
  ]
}
```

**`axis_max`**: 20問全部回答した場合の各軸の理論上最大生スコア。正規化（0〜100）のスケーリングに使用。**問いを変更したら再計算が必要**（全問A選択時の各軸合計を求める）。

**`condition`**: `{ "axis": ">N" }` の形式でAND条件。types配列の**上から順**に評価し、最初にマッチしたタイプが選択されます。条件のないものがデフォルト。

**対応演算子**: `>`, `<`, `>=`, `<=`, `=`

### `data/results.db`（SQLite）

スキーマ:
```sql
CREATE TABLE results (
    id         TEXT PRIMARY KEY,   -- UUID v4
    created_at TEXT NOT NULL,      -- ISO8601 UTC
    answers    TEXT NOT NULL,      -- JSON配列 ["A","C",null,...]
    scores     TEXT NOT NULL,      -- JSON {"independence":72,...}
    type_id    TEXT NOT NULL       -- タイプID
);
```

全来場者の軸平均との差分（`axis_comparisons`）は、結果取得時にDBから計算されます。

---

## 12. スコアリング・タイプ判定ロジック

`backend/scoring.py`

```
1. active.json の順番で active_questions を取得
2. 各回答の scoring デルタを生スコアに加算（null回答はスキップ）
3. 正規化: round(raw[axis] / axis_max[axis] * 100)、0〜100にクランプ
4. types.json の condition を上から評価 → 最初にマッチしたタイプを採用
5. マッチなし → default_type のタイプを使用
```

**注意**: 生スコアが負になる可能性があります（例: 全問D選択で independence が大幅マイナス）。クランプにより0になります。

---

## 13. 印刷プロセス

`backend/printer.py`

```
POST /api/print/{result_id}
  ↓
Chrome headless を起動
  └─ http://localhost:3000/result/{result_id} を開く
  └─ --print-to-pdf で /tmp/xxx.pdf に書き出し
  └─ --virtual-time-budget=5000（最大5秒待機）
  ↓
lpr -P EPSON_SC_PX1V /tmp/xxx.pdf
  ↓
一時PDFを削除
```

**プリンター名の変更**: `printer.py:59` の `-P EPSON_SC_PX1V` を変更。  
**プリンター名確認**: `lpstat -p`  
**キュー確認**: `lpq -P <プリンター名>`  
**キューリセット**: `cancel -a <プリンター名>`

フロントエンドの印刷ボタンは `print:hidden` クラスで印刷紙面に出ません。

---

## 14. よくあるトラブル

### バックエンドが起動しない
```bash
# .venv のPythonを明示的に使う
cd backend
.venv/bin/uvicorn main:app --reload --port 8000
```

### `Arial Unicode.ttf` が見つからない
`sheet.py` の `_FONT_PATH` を修正:
```python
_FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"  # ← 存在するフォントパスに変更
```
確認: `ls /Library/Fonts/*.ttf | grep -i unicode`

### スマホでカメラが起動しない
- HTTPSでアクセスしているか確認（`https://`で始まるngrok URL）
- ブラウザのカメラ権限を確認（設定 → Safari/Chrome → カメラ）
- `/debug` ページでも同じカメラ起動処理なので先に試せる

### 基準マーク未検出エラー
- `GET /debug` でデバッグ画像を確認
- シートの4隅の黒い正方形が全て映っているか確認
- 照明が暗すぎる / 反射が強いと失敗しやすい
- シートを平らに伸ばして撮影する
- `MARK_SIZE_PT` の面積フィルタが厳しすぎる場合は `_find_registration_marks` の `min_area * 0.15` / `max_area * 5.0` の係数を調整

### バブル検出がずれる
- `/debug` のデバッグ画像で赤い中心点の位置を確認
- 別のPDFからシートを印刷した場合、座標がずれる可能性がある
- 再計測: `python3 -c "import fitz; ..."` でPyMuPDFによる座標抽出（後述の拡張ガイド参照）

### Python 3.9 での型ヒント注意
Python 3.9 では `list[str | None]` の union 構文が使えません。`Optional[str]` と `from typing import Optional` を使ってください。

---

## 15. 機能拡張ガイド

### 問いを追加・入れ替える

1. `data/questions.json` に問いを追加（IDはユニーク、形式は既存に合わせる）
2. `data/active.json` の `active_ids` を更新（最大20問、順番がシートの行順）
3. `data/types.json` の `axis_max` を再計算（全問A選択時の最大生スコアを求める）
4. `GET /api/sheet/pdf` でシートPDFを再生成・再印刷

### タイプを追加・変更する

`data/types.json` の `types` 配列に追加するだけ。conditionの評価順に注意（上から）。必ず1つは `condition` なし（デフォルトタイプ）を残す。

### 新しいマークシートPDFで座標を再計測する

```python
import fitz  # pip install pymupdf

doc = fitz.open("marksheet.pdf")
page = doc[0]

# 全矩形（基準マークやバブル輪郭）を取得
paths = page.get_drawings()
for p in paths[:30]:
    print(p["rect"], p["fill"])
```

基準マークは4隅の大きな黒い正方形、バブルは円（rectが正方形に近い小さなもの）として現れます。計測した値で `omr.py` の定数を更新し、`test_omr.py` を実行して5テストが全て通ることを確認してください。

### 軸を追加する

1. `data/questions.json` の `scoring` に新軸のデルタを追加
2. `data/types.json` の `axis_max` に新軸を追加
3. `data/types.json` の `condition` に必要なら条件を追加
4. `frontend/components/ResultCard.tsx` の `AXIS_LABEL` と `AXIS_ICON` に表示名を追加

### 問い数を20問以外にする

`omr.py` は `HALF_ROWS = 10`（1列あたり最大10行）で固定されています。10問以下なら左列のみ、11〜20問なら両列を使います。20問を超える場合は行数の増加に対応する `_ROW_Y_PTS` の追加と、シートレイアウトの変更が必要です。

### 結果の一覧・管理画面を作る

現在 SQLite に全結果が蓄積されています（`data/results.db`）。管理画面を作る場合は `scoring.py` に以下を追加するのが最速です:

```python
def list_results(limit: int = 100) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT id, created_at, type_id FROM results ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    con.close()
    return [{"id": r[0], "created_at": r[1], "type_id": r[2]} for r in rows]
```

### ngrokの固定ドメインを使う

```bash
# ngrok.com の無料アカウントで固定サブドメインを取得後
ngrok http 3000 --domain=your-fixed-subdomain.ngrok-free.app
```

---

*最終更新: 2026-05-14*
