'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';

interface Props {
  onCapture: (dataUrl: string) => void;
  onError?: (message: string) => void;
  scanning?: boolean;
  scanError?: string | null;
}

const MAX_LONG_EDGE = 1600;
const JPEG_QUALITY = 0.92;

const DETECT_INTERVAL_MS = 700;
const DETECT_PREVIEW_EDGE = 640;
const STABLE_HITS_REQUIRED = 2;

export default function CameraView({ onCapture, onError, scanning = false, scanError = null }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [camError, setCamError] = useState<string | null>(null);
  const [detected, setDetected] = useState(false);

  const loopActive = useRef(false);
  const hitCount = useRef(0);
  const busy = useRef(false);
  const capturedOnce = useRef(false);

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
      loopActive.current = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const captureFull = useCallback(() => {
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

  const grabPreview = useCallback((): string | null => {
    const v = videoRef.current;
    if (!v || !v.videoWidth || !v.videoHeight) return null;
    const longEdge = Math.max(v.videoWidth, v.videoHeight);
    const scale = longEdge > DETECT_PREVIEW_EDGE ? DETECT_PREVIEW_EDGE / longEdge : 1;
    const w = Math.round(v.videoWidth * scale);
    const h = Math.round(v.videoHeight * scale);
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(v, 0, 0, w, h);
    return canvas.toDataURL('image/jpeg', 0.6);
  }, []);

  useEffect(() => {
    if (!ready || scanning || scanError || capturedOnce.current) {
      loopActive.current = false;
      return;
    }
    loopActive.current = true;
    hitCount.current = 0;

    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      if (!loopActive.current) return;
      if (!busy.current) {
        busy.current = true;
        try {
          const preview = grabPreview();
          if (preview) {
            const res = await api.detect(preview);
            if (loopActive.current) {
              if (res.marks_found) {
                hitCount.current += 1;
                setDetected(true);
                if (hitCount.current >= STABLE_HITS_REQUIRED && !capturedOnce.current) {
                  capturedOnce.current = true;
                  loopActive.current = false;
                  captureFull();
                  busy.current = false;
                  return;
                }
              } else {
                hitCount.current = 0;
                setDetected(false);
              }
            }
          }
        } catch {
          // ignore
        } finally {
          busy.current = false;
        }
      }
      if (loopActive.current) timer = setTimeout(tick, DETECT_INTERVAL_MS);
    };

    timer = setTimeout(tick, DETECT_INTERVAL_MS);
    return () => {
      loopActive.current = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, scanning, scanError]);

  useEffect(() => {
    if (!scanning && !scanError) {
      capturedOnce.current = false;
      setDetected(false);
      hitCount.current = 0;
    }
  }, [scanning, scanError]);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-full overflow-hidden rounded-2xl border-2 border-navy/30 bg-black">
        <video ref={videoRef} playsInline muted autoPlay className="block w-full" />

        {ready && !camError && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div
              className={`m-6 flex-1 self-stretch rounded-2xl border-4 transition-colors duration-200 ${
                detected ? 'border-emerald-400' : 'border-white/40'
              }`}
              style={{ borderStyle: 'dashed' }}
            />
          </div>
        )}

        {!ready && !camError && (
          <div className="absolute inset-0 flex items-center justify-center text-white/80">
            カメラ起動中…
          </div>
        )}

        {camError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-red-900/80 px-4 text-center text-white">
            <div className="text-lg font-bold">カメラを開けませんでした</div>
            <div className="text-sm opacity-90">{camError}</div>
          </div>
        )}

        {scanning && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/60">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-white/30 border-t-white" />
            <p className="text-white font-bold text-sm">読み取り中…</p>
          </div>
        )}

        {scanError && !scanning && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/70 px-6 text-center">
            <div className="text-4xl">⚠️</div>
            <p className="text-white font-bold text-sm">{scanError}</p>
            <p className="text-white/70 text-xs">マークシートを枠に合わせてください</p>
          </div>
        )}

        {ready && !scanning && !scanError && (
          <div className="absolute bottom-3 left-0 right-0 flex justify-center">
            <div className={`rounded-full px-4 py-1 text-sm text-white transition-colors ${detected ? 'bg-emerald-600/80' : 'bg-black/50'}`}>
              {detected ? 'マークシートを検出！そのまま静止…' : 'マークシートを枠に合わせてください'}
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => { capturedOnce.current = true; captureFull(); }}
        disabled={!ready || scanning}
        className="w-full max-w-sm rounded-2xl bg-navy px-8 py-5 text-xl font-bold text-white shadow-lg disabled:opacity-40 active:translate-y-px"
      >
        {scanning ? '読み取り中…' : '手動で読み取る'}
      </button>

      <p className="text-center text-xs text-navy/60">
        枠内にマークシートをかざすと自動で読み取ります
      </p>
    </div>
  );
}
