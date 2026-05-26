'use client';

import { useRef, useState, useCallback } from 'react';

export default function DebugPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [started, setStarted] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const startCamera = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
    });
    streamRef.current = stream;
    const video = videoRef.current!;
    video.addEventListener('canplay', () => setIsReady(true), { once: true });
    video.srcObject = stream;
    setStarted(true);
    await video.play().catch(() => {});
    setTimeout(() => setIsReady(true), 3000);
  }, []);

  const capture = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')!.drawImage(video, 0, 0);
    const base64 = canvas.toDataURL('image/jpeg', 0.9).replace(/^data:image\/jpeg;base64,/, '');

    setLoading(true);
    setResult(null);
    try {
      const res = await fetch('/api/debug/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64 }),
      });
      setResult(await res.json());
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <main className="min-h-screen bg-slate-900 text-white p-4">
      <h1 className="text-xl font-bold mb-4">OMR デバッグ</h1>

      <div className={!started ? 'hidden' : ''}>
        <video ref={videoRef} autoPlay playsInline muted className="w-full rounded-lg mb-3" />
      </div>
      <canvas ref={canvasRef} className="hidden" />

      {!started && (
        <button onClick={startCamera}
          className="w-full py-4 bg-white text-slate-900 font-bold rounded-full mb-4">
          カメラを起動する
        </button>
      )}

      {isReady && (
        <button onClick={capture} disabled={loading}
          className="w-full py-4 bg-blue-500 text-white font-bold rounded-full mb-4 disabled:opacity-50">
          {loading ? '解析中...' : '📷 撮影して解析'}
        </button>
      )}

      {result && (
        <div className="space-y-4">
          <div className="bg-slate-800 rounded-lg p-3">
            <p className="text-sm font-bold mb-1">基準マーク: {result.marks_found ? '✅ 検出' : '❌ 未検出'}</p>
            <p className="text-xs text-slate-400">画像サイズ: {(result.image_size as number[])?.join(' x ')}</p>
            {!!result.error && <p className="text-red-400 text-sm mt-1">{result.error as string}</p>}
          </div>

          {!!result.debug_image && (
            <div>
              <p className="text-sm font-bold mb-1">
                {result.marks_found ? '透視補正後（緑=塗りあり）' : '二値化結果（マーク確認用）'}
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`data:image/jpeg;base64,${result.debug_image}`} alt="debug" className="w-full rounded-lg" />
            </div>
          )}

          {Array.isArray(result.answers) && result.answers && (
            <div className="bg-slate-800 rounded-lg p-3">
              <p className="text-sm font-bold mb-2">検出回答（解答用紙順）</p>
              {/* 解答用紙と同じ2列: 左Q1-10 / 右Q11-20 */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                {Array.from({ length: 10 }, (_, row) => {
                  const answers = result.answers as (string | null)[];
                  const li = row, ri = row + 10;
                  return (
                    <>
                      <div key={`l${row}`} className={`p-1 rounded text-center ${answers[li] ? 'bg-green-700' : 'bg-slate-700'}`}>
                        Q{li + 1}: {answers[li] ?? '–'}
                      </div>
                      {ri < answers.length ? (
                        <div key={`r${row}`} className={`p-1 rounded text-center ${answers[ri] ? 'bg-green-700' : 'bg-slate-700'}`}>
                          Q{ri + 1}: {answers[ri] ?? '–'}
                        </div>
                      ) : <div key={`re${row}`} />}
                    </>
                  );
                })}
              </div>
            </div>
          )}

          {Array.isArray(result.bubble_ratios) && result.bubble_ratios && (
            <div className="bg-slate-800 rounded-lg p-3">
              <p className="text-sm font-bold mb-2">バブル充填率（解答用紙順）</p>
              <div className="grid grid-cols-2 gap-x-4 text-xs font-mono">
                {Array.from({ length: 10 }, (_, row) => {
                  const ratios = result.bubble_ratios as number[][];
                  const leftRow = ratios[row];
                  const rightRow = ratios[row + 10];
                  const answers = result.answers as (string | null)[];
                  const renderRow = (qIdx: number, qRatios: number[] | undefined) => {
                    if (!qRatios) return <div key={`e${qIdx}`} />;
                    const maxR = Math.max(...qRatios);
                    return (
                      <div key={qIdx} className="flex gap-1 items-center py-0.5">
                        <span className="text-slate-400 w-6">Q{qIdx + 1}</span>
                        {qRatios.map((r, c) => (
                          <span key={c} className={
                            r === maxR && answers[qIdx] ? 'text-green-400 font-bold' : 'text-slate-400'
                          }>
                            {['A','B','C','D'][c]}:{r.toFixed(2)}
                          </span>
                        ))}
                      </div>
                    );
                  };
                  return (
                    <>
                      {renderRow(row, leftRow)}
                      {renderRow(row + 10, rightRow)}
                    </>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
