'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface Props {
  onCapture: (dataUrl: string) => void;
  onError?: (message: string) => void;
  scanning?: boolean;
  scanError?: string | null;
}

const MAX_LONG_EDGE = 1600;
const JPEG_QUALITY = 0.92;

export default function CameraView({ onCapture, onError, scanning = false, scanError = null }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [camError, setCamError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        const msg = 'このブラウザはカメラに対応していません';
        setCamError(msg); onError?.(msg); return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1440 } },
        });
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        const v = videoRef.current;
        if (v) {
          v.srcObject = stream;
          await v.play().catch(() => undefined);
          setReady(true);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'カメラの起動に失敗しました';
        setCamError(msg); onError?.(msg);
      }
    }
    start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const capture = useCallback(() => {
    const v = videoRef.current;
    if (!v || !v.videoWidth || !v.videoHeight) return;
    const longEdge = Math.max(v.videoWidth, v.videoHeight);
    const scale = longEdge > MAX_LONG_EDGE ? MAX_LONG_EDGE / longEdge : 1;
    const w = Math.round(v.videoWidth * scale);
    const h = Math.round(v.videoHeight * scale);
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(v, 0, 0, w, h);
    onCapture(canvas.toDataURL('image/jpeg', JPEG_QUALITY));
  }, [onCapture]);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-full overflow-hidden rounded-2xl border-2 border-navy/30 bg-black">
        <video ref={videoRef} playsInline muted autoPlay className="block w-full" />

        {/* カメラ起動中 */}
        {!ready && !camError && (
          <div className="absolute inset-0 flex items-center justify-center text-white/80">
            カメラ起動中…
          </div>
        )}

        {/* カメラエラー */}
        {camError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-red-900/80 px-4 text-center text-white">
            <div className="text-lg font-bold">カメラを開けませんでした</div>
            <div className="text-sm opacity-90">{camError}</div>
          </div>
        )}

        {/* スキャン中オーバーレイ */}
        {scanning && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/60">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-white/30 border-t-white" />
            <p className="text-white font-bold text-sm">読み取り中…</p>
          </div>
        )}

        {/* スキャンエラーオーバーレイ */}
        {scanError && !scanning && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/70 px-6 text-center">
            <div className="text-4xl">⚠️</div>
            <p className="text-white font-bold text-sm">{scanError}</p>
            <p className="text-white/70 text-xs">もう一度撮影してください</p>
          </div>
        )}

        {/* 待機中ガイド */}
        {ready && !scanning && !scanError && (
          <div className="absolute bottom-3 left-0 right-0 flex justify-center">
            <div className="rounded-full bg-black/50 px-4 py-1 text-sm text-white">
              マークシートを映してください
            </div>
          </div>
        )}
      </div>

      {/* シャッターボタン */}
      <button
        type="button"
        onClick={capture}
        disabled={!ready || scanning}
        className="w-full max-w-sm rounded-2xl bg-navy px-8 py-5 text-xl font-bold text-white shadow-lg disabled:opacity-40 active:translate-y-px"
      >
        {scanning ? '読み取り中…' : '読み取る'}
      </button>

      <p className="text-center text-xs text-navy/60">
        マークシート全体が映ったら「読み取る」を押してください
      </p>
    </div>
  );
}
