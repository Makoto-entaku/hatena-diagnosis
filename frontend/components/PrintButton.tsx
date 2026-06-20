'use client';

/**
 * 結果ページの印刷ボタン。
 *
 * 2系統の動作:
 *   1. ?print=1 でクエリが付いている場合(Chrome headless 経由): ボタンは
 *      非表示にして、自動印刷フローを邪魔しない。
 *   2. 通常のブラウザ表示の場合: クリックで /api/print/{id} を叩く。
 */
import { useEffect, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { cx } from '@/lib/utils';

interface Props {
  station?: number;
  resultId: string;
}

export default function PrintButton({ resultId, station = 1 }: Props) {
  const [status, setStatus] = useState<'idle' | 'sending' | 'ok' | 'error'>(
    'idle',
  );
  const [message, setMessage] = useState<string | null>(null);

  // headless 経由ならボタン自体を表示しない
  const [isHeadless, setIsHeadless] = useState(false);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    setIsHeadless(params.get('print') === '1');
  }, []);

  if (isHeadless) return null;

  async function onClick() {
    setStatus('sending');
    setMessage(null);
    try {
      await api.print(resultId, station);
      setStatus('ok');
      setMessage('プリンタに送りました');
    } catch (e: unknown) {
      setStatus('error');
      setMessage(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : '印刷に失敗しました',
      );
    }
  }

  return (
    <div className="print-hidden flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={onClick}
        disabled={status === 'sending'}
        className={cx(
          'w-full max-w-sm rounded-2xl px-6 py-4 text-lg font-bold text-white shadow transition',
          status === 'sending'
            ? 'bg-navy/60'
            : 'bg-navy hover:bg-navy-deep active:translate-y-px',
        )}
      >
        {status === 'sending' ? '送信中…' : '結果を印刷する'}
      </button>
      {message && (
        <p
          className={cx(
            'text-sm',
            status === 'ok' ? 'text-emerald-700' : 'text-red-700',
          )}
        >
          {message}
        </p>
      )}
    </div>
  );
}
