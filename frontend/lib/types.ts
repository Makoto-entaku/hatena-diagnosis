/**
 * バックエンド API のレスポンス型定義。
 */

export type Answer = 'A' | 'B' | 'C' | 'D' | string | null;
export type ScanStatus = 'ok' | 'blank' | 'multi' | 'unclear';

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

export interface ScanResponse {
  answers: Answer[];
  statuses: ScanStatus[];
  question_count: number;
  error: string | null;
  number_answers: Record<string, number>;
  marks_found: boolean;
}

export interface DebugScanResponse extends ScanResponse {
  fill_ratios: number[][];
  annotated_image_base64: string | null;
}

export interface SubmitResponse {
  result_id: string;
}

export interface WeirdAnswer {
  question_summary: string;
  answer: string;
  answer_label: string;
  ratio: number;
}

export interface ResultResponse {
  result_id: string;
  created_at: string;
  type_code: string;
  type_id: string;
  type_name: string;
  tagline: string;
  description: string;
  tendency: string;
  advice: string;
  suited: string;
  strength: string;
  scores: Record<string, number>;
  display_scores: Record<string, number>;
  raw_answers: Answer[];
  questions: ActiveQuestion[];
  axis_comparisons: Record<string, number>;
  weird_answers: WeirdAnswer[];
}
