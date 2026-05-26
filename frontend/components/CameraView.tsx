'use client';

/**
 * カメラ起動 → プレビュー → 撮影 → JPEG dataURL を返す。
 *
 * - getUserMedia の `facingMode: environment` を優先(スマホ背面カメラ)
 * - HTTPS でないと getUserMedia は拒否されるので、本番運用は ngrok 経由
 * - 撮影サイズは長辺 1600px を上限にダウンサイズ(OMR は A4 を 800×1130 に
 *   透視補正するので、これ以上大きくしてもメリットが薄く転送量だけ増える)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { cx } from '@/lib/utils';

interface Props {
  /** 撮影完了時に呼ばれる。引数は "data:image/jpeg;base64,..." 形式。 */
  onCapture: (dataUrl: string) => void;
  /** カメラ起動エラーを親に通知したい場合。 */
  onError?: (message: string) => void;
  /** 撮影ボタンのラベル。 */
  captureLabel?: string;
}

const MAX_LONG_EDGE = 1600;
const JPEG_QUALITY = 0.92;

export default function CameraView({
  onCapture,
  onError,
  captureLabel = '撮影する',
}: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // カメラ起動
  useEffect(() => {
    let cancelled = false;

    async function start() {
      if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        const msg = 'このブラウザはカメラに対応していません(HTTPSで開いていますか?)';
        setError(msg);
        onError?.(msg);
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: 'environment' },
            width:  { ideal: 1920 },
            height: { ideal: 1440 },
          },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const v = videoRef.current;
        if (v) {
          v.srcObject = stream;
          await v.play().catch(() => undefined);
          setReady(true);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'カメラの起動に失敗しました';
        setError(msg);
        onError?.(msg);
      }
    }

    start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
    // onError を依存に入れると親の関数アイデンティティ依存になり停止/起動を繰り返す
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const capture = useCallback(() => {
    const v = videoRef.current;
    if (!v || !v.videoWidth || !v.videoHeight) return;

    // 長辺 MAX_LONG_EDGE にダウンサイズ
    const longEdge = Math.max(v.videoWidth, v.videoHeight);
    const scale = longEdge > MAX_LONG_EDGE ? MAX_LONG_EDGE / longEdge : 1;
    const w = Math.round(v.videoWidth * scale);
    const h = Math.round(v.videoHeight * scale);

    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(v, 0, 0, w, h);
    const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
    onCapture(dataUrl);
  }, [onCapture]);

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-full overflow-hidden rounded-2xl border-2 border-navy/30 bg-black">
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          className="block w-full"
        />
        {!ready && !error && (
          <div className="absolute inset-0 flex items-center justify-center text-white/80">
            カメラ起動中…
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-red-900/80 px-4 text-center text-white">
            <div className="text-lg font-bold">カメラを開けませんでした</div>
            <div className="text-sm opacity-90">{error}</div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={capture}
        disabled={!ready}
        className={cx(
          'w-full rounded-2xl px-6 py-4 text-lg font-bold shadow transition',
          ready
            ? 'bg-navy text-white hover:bg-navy-deep active:translate-y-px'
            : 'bg-gray-300 text-gray-500',
        )}
      >
        {captureLabel}
      </button>

      <p className="text-center text-xs text-navy/60">
        マークシート全体が映るように、4隅の黒い ▣ がはみ出さないよう撮影してください。
      </p>
    </div>
  );
}
