'use client';

/**
 * OMR 後の回答確認・手動修正画面。
 *
 * - 2 列グリッド(左 Q1〜10、右 Q11〜20)
 * - 各問にステータスドット
 * - A/B/C/D ボタン(同じボタンを再タップで選択解除 = blank に戻す)
 * - 要確認・未回答カウントのバッジ
 */
import { useMemo } from 'react';
import type { ActiveQuestion, Answer, ScanStatus } from '@/lib/types';
import { StatusDot } from './StatusBadge';
import { cx } from '@/lib/utils';

interface Props {
  questions: ActiveQuestion[];
  answers: Answer[];
  statuses: ScanStatus[];
  /** 1 問を更新する。 */
  onChange: (index: number, ans: Answer) => void;
  /** 確定ボタン押下。 */
  onSubmit: () => void;
  /** 再撮影ボタン押下。 */
  onRetake: () => void;
  /** Submit 中なら true。 */
  submitting?: boolean;
}

const CHOICES: Array<'A' | 'B' | 'C' | 'D'> = ['A', 'B', 'C', 'D'];

export default function ReviewScreen({
  questions,
  answers,
  statuses,
  onChange,
  onSubmit,
  onRetake,
  submitting = false,
}: Props) {
  const { blanks, attentions } = useMemo(() => {
    let blanks = 0;
    let attentions = 0;
    answers.forEach((a, i) => {
      if (a === null) blanks++;
      const st = statuses[i];
      if (st === 'multi' || st === 'unclear') attentions++;
    });
    return { blanks, attentions };
  }, [answers, statuses]);

  // 左Q1-10 / 右Q11-20 のレイアウト
  const half = Math.ceil(questions.length / 2);
  const leftIdx = questions.map((_, i) => i).slice(0, half);
  const rightIdx = questions.map((_, i) => i).slice(half);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <header className="mb-5 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-navy">回答の確認</h1>
        <div className="flex gap-2 text-xs">
          <span className="rounded-full bg-orange-100 px-3 py-1 font-bold text-orange-700">
            要確認 {attentions}
          </span>
          <span className="rounded-full bg-gray-100 px-3 py-1 font-bold text-gray-700">
            未回答 {blanks}
          </span>
        </div>
      </header>

      <p className="mb-4 text-sm text-navy/70">
        正しい場合はそのまま「確定して診断する」を押してください。修正したい問は
        A/B/C/D をタップ(同じボタンをもう一度押すと未回答に戻ります)。
      </p>

      <div className="grid gap-x-6 gap-y-3 md:grid-cols-2">
        {[leftIdx, rightIdx].map((indices, col) => (
          <ul key={col} className="space-y-2">
            {indices.map((i) => {
              const q = questions[i];
              const ans = answers[i];
              const st = statuses[i];
              return (
                <li
                  key={q.id}
                  className="rounded-xl border border-navy/15 bg-white px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
                      Q{i + 1}
                    </span>
                    <StatusDot status={st} />
                    <span className="truncate text-sm font-medium text-navy">
                      {q.summary || q.text}
                    </span>
                  </div>

                  <div className="mt-2 grid grid-cols-4 gap-1.5">
                    {CHOICES.map((c) => {
                      const active = ans === c;
                      return (
                        <button
                          key={c}
                          type="button"
                          onClick={() => onChange(i, active ? null : c)}
                          className={cx(
                            'rounded-lg px-2 py-2 text-sm font-bold transition',
                            active
                              ? 'bg-navy text-white shadow'
                              : 'bg-cream text-navy hover:bg-navy/10',
                          )}
                          title={q.options[c]}
                        >
                          <span className="block text-base leading-none">{c}</span>
                          <span className="mt-0.5 block truncate text-[10px] font-normal opacity-80">
                            {q.options[c]}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </li>
              );
            })}
          </ul>
        ))}
      </div>

      <div className="sticky bottom-0 mt-6 -mx-4 flex gap-3 border-t border-navy/10 bg-white/95 px-4 py-3 backdrop-blur">
        <button
          type="button"
          onClick={onRetake}
          disabled={submitting}
          className="flex-1 rounded-xl border-2 border-navy/30 px-4 py-3 font-bold text-navy disabled:opacity-50"
        >
          撮り直す
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className={cx(
            'flex-[2] rounded-xl px-4 py-3 font-bold text-white shadow transition',
            submitting ? 'bg-navy/60' : 'bg-navy hover:bg-navy-deep',
          )}
        >
          {submitting ? '診断中…' : '確定して診断する'}
        </button>
      </div>
    </div>
  );
}
