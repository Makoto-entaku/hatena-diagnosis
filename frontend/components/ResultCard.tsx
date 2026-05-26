/**
 * 16タイプ診断の結果カード。SSR でレンダリングする想定。
 *
 * セクション構成:
 *   1. ヘッダー(タイプ名・タグライン・紺背景)
 *   2. タイプセクション(動物イラスト・タイプ名・説明)
 *   3. スコアレーダー(5軸)
 *   4. 全来場者比較(±差分)
 *   5. 基本傾向
 *   6. 対人運アップのひとこと
 *   7. 20問の回答一覧(2列)
 *   8. 印刷ボタン(print:hidden)
 */
import type { ResultResponse } from '@/lib/types';
import ScoreRadar from './ScoreRadar';
import TypeIllustration from './TypeIllustration';
import PrintButton from './PrintButton';

/** display_name → axis_id のマップ。types.json と一致。 */
const DISPLAY_TO_AXIS: Record<string, string> = {
  社交度: 'social',
  心の広さ度: 'tolerance',
  怠惰度: 'action',
  自分大切度: 'self',
  ロジカル度: 'logical',
};

const COMPARISON_LABELS: Array<[string, string]> = [
  ['社交度', 'social'],
  ['心の広さ度', 'tolerance'],
  ['怠惰度', 'action'],
  ['自分大切度', 'self'],
  ['ロジカル度', 'logical'],
];

function formatDiff(value: number): string {
  if (value === 0) return '±0.0';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}`;
}

function getDiff(result: ResultResponse, axisId: string): number {
  return result.axis_comparisons[axisId] ?? 0;
}

export default function ResultCard({ result }: { result: ResultResponse }) {
  return (
    <article className="mx-auto max-w-3xl px-4 py-6 print:px-0 print:py-0">
      {/* 1. ヘッダー */}
      <header className="rounded-3xl bg-navy px-6 py-5 text-white shadow-md print-keep-color print:rounded-none print:shadow-none">
        <div className="text-xs font-bold tracking-widest opacity-80">
          16タイプ診断 / TYPE {result.type_code}
        </div>
        <h1 className="mt-1 text-3xl font-bold leading-tight">
          {result.type_name}
        </h1>
        <p className="mt-1 text-sm opacity-90">{result.tagline}</p>
      </header>

      {/* 2. タイプセクション */}
      <section className="mt-5 flex flex-col items-center gap-4 rounded-3xl bg-white px-6 py-6 shadow-sm md:flex-row md:items-start print:rounded-none print:shadow-none">
        <TypeIllustration
          typeId={result.type_id}
          typeName={result.type_name}
          size={150}
        />
        <div className="flex-1">
          <h2 className="text-xl font-bold text-navy">{result.type_name}</h2>
          <p className="mt-2 text-sm leading-relaxed text-navy/90">
            {result.description}
          </p>
        </div>
      </section>

      {/* 3. スコアレーダー */}
      <section className="mt-5 rounded-3xl bg-white px-4 py-6 shadow-sm print:rounded-none print:shadow-none">
        <h2 className="text-center text-lg font-bold text-navy">
          5軸スコア
        </h2>
        <div className="mt-2 flex justify-center">
          <ScoreRadar scores={result.display_scores} size={340} />
        </div>
      </section>

      {/* 4. 全来場者比較 */}
      <section className="mt-5 rounded-3xl bg-white px-6 py-5 shadow-sm print:rounded-none print:shadow-none">
        <h2 className="text-lg font-bold text-navy">全来場者との比較</h2>
        <p className="mt-1 text-xs text-navy/60">
          これまでの来場者全員の軸平均との差分(±)
        </p>
        <ul className="mt-3 grid grid-cols-2 gap-y-1.5 text-sm md:grid-cols-5">
          {COMPARISON_LABELS.map(([label, axisId]) => {
            const diff = getDiff(result, axisId);
            const positive = diff > 0;
            const neutral = diff === 0;
            return (
              <li
                key={axisId}
                className="flex items-baseline justify-between gap-2 md:flex-col md:items-center md:justify-start"
              >
                <span className="font-bold text-navy">{label}</span>
                <span
                  className={
                    neutral
                      ? 'text-navy/70'
                      : positive
                        ? 'font-bold text-emerald-700'
                        : 'font-bold text-rose-700'
                  }
                >
                  {formatDiff(diff)}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      {/* 5. 基本傾向 */}
      <section className="mt-5 rounded-3xl bg-white px-6 py-5 shadow-sm print:rounded-none print:shadow-none">
        <h2 className="text-lg font-bold text-navy">基本傾向</h2>
        <p className="mt-2 text-sm leading-relaxed text-navy/90">
          {result.tendency}
        </p>
      </section>

      {/* 6. 対人運アップのひとこと */}
      <section className="mt-5 rounded-3xl bg-cream px-6 py-5 shadow-sm print-keep-color print:rounded-none print:shadow-none">
        <h2 className="text-lg font-bold text-navy">対人運アップのひとこと</h2>
        <p className="mt-2 text-sm leading-relaxed text-navy/90">
          {result.advice}
        </p>
      </section>

      {/* 7. 20問の回答一覧 */}
      <section className="mt-5 rounded-3xl bg-white px-6 py-5 shadow-sm print:rounded-none print:shadow-none">
        <h2 className="text-lg font-bold text-navy">あなたの回答 (20問)</h2>
        <ol className="mt-3 grid gap-x-6 gap-y-1.5 text-xs md:grid-cols-2">
          {result.questions.map((q, i) => {
            const ans = result.raw_answers[i];
            const label = ans ? q.options[ans] : '未回答';
            return (
              <li key={q.id} className="flex items-start gap-2 leading-snug">
                <span className="mt-0.5 inline-flex h-5 w-7 shrink-0 items-center justify-center rounded-md bg-navy text-[10px] font-bold text-white print-keep-color">
                  Q{i + 1}
                </span>
                <span className="flex-1 text-navy/85">
                  {q.summary || q.text}
                </span>
                <span className="inline-flex items-center gap-1 whitespace-nowrap">
                  <span
                    className={
                      ans
                        ? 'rounded-md bg-navy/10 px-1.5 py-0.5 font-bold text-navy'
                        : 'rounded-md bg-gray-100 px-1.5 py-0.5 text-gray-500'
                    }
                  >
                    {ans ?? '—'}
                  </span>
                  <span className="max-w-[10rem] truncate text-navy/70">
                    {label}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      {/* 8. 印刷ボタン(print:hidden) */}
      <div className="mt-8 flex justify-center">
        <PrintButton resultId={result.result_id} />
      </div>

      <footer className="print-hidden mt-6 text-center text-xs text-navy/50">
        result_id: <code>{result.result_id}</code>
      </footer>

      {/* eslint-disable-next-line @typescript-eslint/no-unused-expressions */}
      {DISPLAY_TO_AXIS && null}
    </article>
  );
}
