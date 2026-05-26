/**
 * フロントエンド共通の API fetch ラッパー。
 *
 * - すべて /api/... の相対パスで叩く(next.config.mjs の rewrite で :8000 へ転送)
 * - サーバーコンポーネントから呼ぶ場合は絶対 URL が必要なため、
 *   FRONTEND_BASE_URL / NEXT_PUBLIC_API_BASE_URL を見て解決する
 */
import type {
  ActiveResponse,
  DebugScanResponse,
  ResultResponse,
  ScanResponse,
  SubmitResponse,
  Answer,
} from './types';

/** クライアント or サーバーで使える絶対URLを作る。 */
function resolveUrl(path: string): string {
  // ブラウザ側では相対パスで OK(Next.js が rewrite する)
  if (typeof window !== 'undefined') return path;

  // サーバー側では絶対 URL が必要。FRONTEND_BASE_URL があれば優先、
  // なければバックエンドに直接(/api/result/... を localhost:8000 で叩く)。
  const base =
    process.env.FRONTEND_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.BACKEND_URL ||
    'http://localhost:8000';
  return new URL(path, base).toString();
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(resolveUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    // サーバー側で取得するときは常に最新のデータを取りに行く
    cache: 'no-store',
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** 有効な問いの一覧を取得。 */
  getActive: () => request<ActiveResponse>('/api/active'),

  /** 画像から回答を読み取る(保存なし)。 */
  scan: (imageDataUrl: string) =>
    request<ScanResponse>('/api/scan', {
      method: 'POST',
      body: JSON.stringify({ image: imageDataUrl }),
    }),

  /** デバッグ用スキャン。 */
  debugScan: (imageDataUrl: string) =>
    request<DebugScanResponse>('/api/debug/scan', {
      method: 'POST',
      body: JSON.stringify({ image: imageDataUrl }),
    }),

  /** 回答を確定して保存。 */
  submit: (answers: Answer[]) =>
    request<SubmitResponse>('/api/submit', {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),

  /** 結果取得(SSR からも使う)。 */
  getResult: (id: string) =>
    request<ResultResponse>(`/api/result/${encodeURIComponent(id)}`),

  /** 印刷キューに送る。 */
  print: (id: string) =>
    request<{ status?: string; [k: string]: unknown }>(
      `/api/print/${encodeURIComponent(id)}`,
      { method: 'POST' },
    ),
};

export { ApiError };
