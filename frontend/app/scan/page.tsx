'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import CameraView from '@/components/CameraView';
import { api, ApiError } from '@/lib/api';
import type { ActiveQuestion, Answer, ScanStatus } from '@/lib/types';

type Phase = 'top' | 'camera' | 'confirm' | 'submitting';

function ScanPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const station = searchParams.get('station') ?? '1';
  const [phase, setPhase] = useState<Phase>('camera');
  const [questions, setQuestions] = useState<ActiveQuestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [statuses, setStatuses] = useState<ScanStatus[]>([]);
  const [scanning, setScanning] = useState(false);
  const [numberAnswers, setNumberAnswers] = useState<Record<string, number>>({});
  const [scanError, setScanError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getActive().then((res) => {
      if (cancelled) return;
      setQuestions(res.questions);
    }).catch((e: unknown) => {
      if (cancelled) return;
      setError(e instanceof Error ? e.message : '問い一覧の取得に失敗しました');
    });
    return () => { cancelled = true; };
  }, []);

  const onCapture = useCallback(async (dataUrl: string) => {
    setScanning(true);
    setScanError(null);
    setCapturedImage(dataUrl);
    try {
      const scanRes = await api.scan(dataUrl);
      if (scanRes.error) {
        setScanError(scanRes.error);
        setScanning(false);
        return;
      }
      setAnswers(scanRes.answers);
      setStatuses(scanRes.statuses);
      setNumberAnswers(scanRes.number_answers ?? {});
      setScanning(false);
      setPhase('confirm');
    } catch (e: unknown) {
      setScanError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'スキャンに失敗しました');
      setScanning(false);
    }
  }, []);

  const onRetake = useCallback(() => {
    setError(null);
    setScanError(null);
    setCapturedImage(null);
    setPhase('camera');
  }, []);

  const onConfirmSubmit = useCallback(async () => {
    setError(null);
    setPhase('submitting');
    try {
      const submitRes = await api.submit(answers, numberAnswers);
      router.push(`/result/${submitRes.result_id}?station=${station}`);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : '送信に失敗しました');
      setPhase('confirm');
    }
  }, [answers, router, station]);

  if (phase === 'top') {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-6 bg-white">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-navy">はてな展</h1>
          <p className="mt-2 text-lg text-navy/70">16タイプ診断</p>
        </div>
        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
        <button type="button" onClick={() => setPhase('camera')} className="w-full max-w-sm rounded-2xl bg-navy px-8 py-6 text-2xl font-bold text-white shadow-lg active:translate-y-px">
          撮影開始
        </button>
        <p className="text-sm text-navy/50">マークシートを用意してからタップしてください</p>
      </main>
    );
  }

  if (phase === 'submitting') {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4">
        <div className="h-14 w-14 animate-spin rounded-full border-4 border-navy/20 border-t-navy" />
        <p className="text-lg font-bold text-navy">診断中…</p>
      </main>
    );
  }

  if (phase === 'confirm') {
    const total = answers.length;
    const blankCount = statuses.filter((s) => s === 'blank').length;
    const attentionCount = statuses.filter((s) => s === 'multi' || s === 'unclear').length;
    const okCount = total - blankCount - attentionCount;
    const hasIssue = blankCount > 0 || attentionCount > 0;

    return (
      <main className="mx-auto max-w-xl px-4 py-6">
        <header className="mb-4">
          <h1 className="text-2xl font-bold text-navy">読み取り結果の確認</h1>
        </header>
        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
        {capturedImage && (
          <div className="overflow-hidden rounded-2xl border-2 border-navy/20">
            <img src={capturedImage} alt="撮影したマークシート" className="block w-full" />
          </div>
        )}
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl bg-emerald-50 px-3 py-2">
            <div className="text-2xl font-bold text-emerald-700">{okCount}</div>
            <div className="text-xs text-emerald-700">読み取りOK</div>
          </div>
          <div className="rounded-xl bg-orange-50 px-3 py-2">
            <div className="text-2xl font-bold text-orange-700">{attentionCount}</div>
            <div className="text-xs text-orange-700">要確認</div>
          </div>
          <div className="rounded-xl bg-gray-100 px-3 py-2">
            <div className="text-2xl font-bold text-gray-700">{blankCount}</div>
            <div className="text-xs text-gray-700">未回答</div>
          </div>
        </div>
        <div className="mt-4 space-y-1">
          {answers.map((a, i) => {
            const status = statuses[i];
            const label = questions[i]?.summary ?? questions[i]?.text ?? `Q${i + 1}`;
            const mark = status === 'ok' ? '○' : status === 'blank' ? '×' : '△';
            const color = status === 'ok' ? 'text-emerald-700 bg-emerald-50' : status === 'blank' ? 'text-gray-700 bg-gray-100' : 'text-orange-700 bg-orange-50';
            return (
              <div key={i} className={`flex items-center justify-between rounded-lg px-3 py-1.5 text-sm ${color}`}>
                <span className="truncate pr-2">{i + 1}. {label}</span>
                <span className="flex shrink-0 items-center gap-2"><span className="min-w-[1.75rem] rounded bg-white/70 px-2 py-0.5 text-center text-base font-bold tabular-nums">{a ?? "—"}</span><span className="font-bold text-lg">{mark}</span></span>
              </div>
            );
          })}
        </div>
        {hasIssue && <p className="mt-3 rounded-xl bg-orange-50 px-3 py-2 text-sm text-orange-800">一部の項目が読み取れていない可能性があります。もう一度撮影するか、このまま送信できます。</p>}
        {!hasIssue && <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">すべての項目が正しく読み取れました！</p>}
        <div className="sticky bottom-0 mt-6 -mx-4 flex gap-3 border-t border-navy/10 bg-white/95 px-4 py-3 backdrop-blur">
          <button type="button" onClick={onRetake} className="flex-1 rounded-xl border-2 border-navy/30 px-4 py-3 font-bold text-navy">撮り直す</button>
          <button type="button" onClick={onConfirmSubmit} className="flex-[2] rounded-xl bg-navy px-4 py-3 font-bold text-white shadow">この内容で送信する</button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-xl px-4 py-6">
      <header className="mb-5 flex items-center gap-3">
        <button type="button" onClick={() => setPhase('top')} className="text-navy/60 underline text-sm">← 戻る</button>
        <h1 className="text-2xl font-bold text-navy">マークシートを撮影</h1>
      </header>
      <CameraView onCapture={onCapture} scanning={scanning} scanError={scanError} />
    </main>
  );
}

export default function ScanPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-navy">読み込み中…</div>}>
      <ScanPageInner />
    </Suspense>
  );
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 w-full">
      <span className="font-bold">エラー:</span>
      <span className="flex-1">{message}</span>
      <button type="button" onClick={onDismiss} className="text-red-700 underline">閉じる</button>
    </div>
  );
}
