import { cx } from '@/lib/utils';
import type { ScanStatus } from '@/lib/types';

const LABEL: Record<ScanStatus, string> = {
  ok:      'OK',
  blank:   '未回答',
  multi:   '複数疑い',
  unclear: '要確認',
};

const STYLE: Record<ScanStatus, string> = {
  ok:      'bg-emerald-500 text-white',
  blank:   'bg-gray-300 text-gray-700',
  multi:   'bg-red-500 text-white',
  unclear: 'bg-orange-400 text-white',
};

export function StatusDot({ status }: { status: ScanStatus }) {
  return (
    <span
      title={LABEL[status]}
      className={cx(
        'inline-block h-3 w-3 rounded-full ring-1 ring-black/10',
        status === 'ok'      && 'bg-emerald-500',
        status === 'blank'   && 'bg-gray-300',
        status === 'multi'   && 'bg-red-500',
        status === 'unclear' && 'bg-orange-400',
      )}
    />
  );
}

export function StatusPill({ status }: { status: ScanStatus }) {
  return (
    <span
      className={cx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold',
        STYLE[status],
      )}
    >
      {LABEL[status]}
    </span>
  );
}
