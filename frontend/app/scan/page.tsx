'use client';

/**
 * /scan — 撮影 → OMR → 確認・修正 → 確定 のメイン画面。
 *
 * 状態機械: idle → loading → review → submitting → (router.push /result/[id])
 */
import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import CameraView from '@/components/CameraView';
import ReviewScreen from '@/components/ReviewScreen';
import { api, ApiError } from '@/lib/api';
import type {
  ActiveQuestion,
  Answer,
  ScanStatus,
} from '@/lib/types';

type Phase = 'idle' | 'loading' | 'review' | 'submitting';

export default function ScanPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>('idle');
  const [questions, setQuestions] = useState<ActiveQuestion[]>([]);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [statuses, setStatuses] = useState<ScanStatus[]>([]);
  const [error, setError] = useState<string | null>(null);

  // 起動時に問い一覧を取得(再撮影しても再取得しないようキャッシュ)
  useEffect(() => {
    let cancelled = false;
    api
      .getActive()
      .then((res) => {
        if (cancelled) return;
        setQuestions(res.questions);
        setAnswers(new Array(res.question_count).fill(null));
        setStatuses(new Array(res.question_count).fill('blank'));
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(
          e instanceof Error
            ? `問い一覧の取得に失敗しました: ${e.message}`
            : '問い一覧の取得に失敗しました',
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 撮影完了 → /api/scan
  const onCapture = useCallback(async (dataUrl: string) => {
    setError(null);
    setPhase('loading');
    try {
      const res = await api.scan(dataUrl);
      if (res.error) {
        setError(res.error);
        setPhase('idle');
        return;
      }
      setAnswers(res.answers);
      setStatuses(res.statuses);
      setPhase('review');
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : 'スキャンに失敗しました';
      setError(msg);
      setPhase('idle');
    }
  }, []);

  const onChange = useCallback((i: number, ans: Answer) => {
    setAnswers((prev) => {
      const next = prev.slice();
      next[i] = ans;
      return next;
    });
    setStatuses((prev) => {
      const next = prev.slice();
      // ユーザーが手動修正したら ok に変える(空にしたら blank)
      next[i] = ans === null ? 'blank' : 'ok';
      return next;
    });
  }, []);

  const onRetake = useCallback(() => {
    setError(null);
    setPhase('idle');
  }, []);

  const onSubmit = useCallback(async () => {
    setError(null);
    setPhase('submitting');
    try {
      const res = await api.submit(answers);
      router.push(`/result/${res.result_id}`);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : '送信に失敗しました';
      setError(msg);
      setPhase('review');
    }
  }, [answers, router]);

  // -------------------------------------------------------------
  // フェーズ別レンダリング
  // -------------------------------------------------------------

  if (phase === 'review' || phase === 'submitting') {
    return (
      <>
        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
        <ReviewScreen
          questions={questions}
          answers={answers}
          statuses={statuses}
          onChange={onChange}
          onSubmit={onSubmit}
          onRetake={onRetake}
          submitting={phase === 'submitting'}
        />
      </>
    );
  }

  // idle / loading
  return (
    <main className="mx-auto max-w-xl px-4 py-6">
      <header className="mb-5">
        <h1 className="text-2xl font-bold text-navy">マークシートを撮影</h1>
        <p className="mt-1 text-sm text-navy/70">
          シート全体を映してから「撮影する」を押してください。
        </p>
      </header>

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      )}

      {phase === 'loading' ? (
        <Loading label="読み取り中…" />
      ) : (
        <CameraView onCapture={onCapture} captureLabel="撮影する" />
      )}
    </main>
  );
}

function Loading({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-navy/30 bg-white py-16">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-navy/20 border-t-navy" />
      <div className="text-navy">{label}</div>
    </div>
  );
}

function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
      <span className="font-bold">エラー:</span>
      <span className="flex-1">{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        className="text-red-700 underline"
      >
        閉じる
      </button>
    </div>
  );
}
