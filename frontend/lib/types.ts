/**
 * バックエンド API のレスポンス型定義。
 *
 * backend/main.py の Pydantic モデル・scoring.get_result() の戻り値と
 * 完全に一致させること。
 */

/** A/B/C/D の4択。未回答は null。 */
export type Answer = 'A' | 'B' | 'C' | 'D' | null;

/** OMR の判定ステータス。 */
export type ScanStatus = 'ok' | 'blank' | 'multi' | 'unclear';

/** /api/active のレスポンス。 */
export interface ActiveQuestion {
  id: string;
  text: string;
  summary: string;
  options: { A: string; B: string; C: string; D: string };
}

export interface ActiveResponse {
  question_count: number;
  questions: ActiveQuestion[];
}

/** /api/scan のレスポンス。 */
export interface ScanResponse {
  answers: Answer[];
  statuses: ScanStatus[];
  question_count: number;
  error: string | null;
}

/** /api/debug/scan のレスポンス。 */
export interface DebugScanResponse extends ScanResponse {
  /** 各問 × 4選択肢の充填率 (0.0〜1.0)。 */
  fill_ratios: number[][];
  /** "data:image/png;base64,..." 形式のアノテーション画像。 */
  annotated_image_base64: string | null;
}

/** /api/submit のレスポンス。 */
export interface SubmitResponse {
  result_id: string;
}

/** /api/result/{id} のレスポンス。 */
export interface ResultResponse {
  result_id: string;
  created_at: string;        // ISO8601 UTC
  type_code: string;         // "IWLS" など
  type_id: string;           // "sloth" など
  type_name: string;
  tagline: string;
  description: string;
  tendency: string;
  advice: string;
  /** 軸IDキー (social/tolerance/action/self/logical) の 0〜100 スコア。 */
  scores: Record<string, number>;
  /** 表示名キー (社交度/心の広さ度/怠惰度/自分大切度/ロジカル度) の 0〜100 スコア。 */
  display_scores: Record<string, number>;
  /** active.json 順の回答配列。長さ = questions.length。 */
  raw_answers: Answer[];
  questions: ActiveQuestion[];
  /** 軸IDキーの「全来場者平均との差分」(±)。 */
  axis_comparisons: Record<string, number>;
}
