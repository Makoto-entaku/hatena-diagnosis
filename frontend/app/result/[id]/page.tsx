/**
 * /result/[id] — 診断結果ページ。
 *
 * SSR で /api/result/{id} を直接取得する。
 * Chrome headless が ?print=1 で開いて A4 PDF 化 → lpr に流す動線にも対応。
 */
import { notFound } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import ResultCard from '@/components/ResultCard';

interface PageProps {
  params: { id: string };
}

export const dynamic = 'force-dynamic';   // SSRで毎回取得
export const revalidate = 0;

export default async function ResultPage({ params }: PageProps) {
  let result;
  try {
    result = await api.getResult(params.id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    // 取得失敗時はわかりやすいエラー画面
    return (
      <main className="mx-auto max-w-xl px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-navy">結果を取得できませんでした</h1>
        <p className="mt-3 text-sm text-navy/70">
          {e instanceof Error ? e.message : '不明なエラー'}
        </p>
        <a
          href="/scan"
          className="mt-6 inline-block rounded-xl bg-navy px-5 py-3 font-bold text-white"
        >
          撮影画面に戻る
        </a>
      </main>
    );
  }

  return <ResultCard result={result} />;
}
