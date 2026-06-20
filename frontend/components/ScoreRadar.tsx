'use client';

import React from 'react';

interface Props {
  scores: Record<string, number>;
  size?: number;
}

const AXES = [
  { id: 'tolerance', label: '心の広さ度', left: 'せまい',     right: '広い',       angle: -90,  labelPos: 'top'   },
  { id: 'social',    label: '社交度',     left: 'ひとり派',   right: '社交的',     angle: -18,  labelPos: 'right' },
  { id: 'action',    label: '怠惰度',     left: 'シャキシャキ', right: 'ぐうたら',   angle:  54,  labelPos: 'br'    },
  { id: 'logical',   label: 'ロジカル度', left: '感情派',     right: 'ロジカル派', angle: 126,  labelPos: 'bl'    },
  { id: 'self',      label: '自分大切度', left: '自己犠牲',   right: '自分優先',   angle: 198,  labelPos: 'left'  },
] as const;

const PINK = '#E8769F';
const PINK_GRID = '#F6C9D9';
const PINK_FILL = 'rgba(232,118,159,0.28)';

export default function ScoreRadar({ scores, size = 95 }: Props) {
  const padX = 78;
  const padY = 82;
  const cx = size / 2 + padX;
  const cy = size / 2 + padY;
  const r = size / 2;
  const totalW = size + padX * 2;
  const totalH = size + padY * 2;

  function pt(angle: number, radius: number): [number, number] {
    const rad = (angle * Math.PI) / 180;
    return [cx + radius * Math.cos(rad), cy + radius * Math.sin(rad)];
  }

  const gridLevels = [0.25, 0.5, 0.75, 1.0];
  const dataPoints = AXES.map((ax) => {
    const score = scores[ax.label] ?? 50;
    const ratio = Math.min(Math.max(score, 0), 100) / 100;
    return pt(ax.angle, r * ratio);
  });
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

  return (
    <svg
      width={totalW}
      height={totalH}
      viewBox={`0 0 ${totalW} ${totalH}`}
      style={{ display: 'block', margin: '0 auto', overflow: 'visible' }}
    >
      <text x={cx} y={cy + r * 0.55} textAnchor="middle" fontSize={r * 2.2} fill="#FBE3EC" fontWeight={900} style={{ opacity: 0.5 }}>?</text>

      {gridLevels.map((level) => {
        const pts = AXES.map((ax) => pt(ax.angle, r * level));
        const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';
        return <path key={level} d={d} fill="none" stroke={PINK_GRID} strokeWidth={1.2} />;
      })}

      {AXES.map((ax) => {
        const [x, y] = pt(ax.angle, r);
        return <line key={ax.id} x1={cx} y1={cy} x2={x} y2={y} stroke={PINK_GRID} strokeWidth={1.2} />;
      })}

      <path d={dataPath} fill={PINK_FILL} stroke={PINK} strokeWidth={2} strokeLinejoin="round" />
      {dataPoints.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3} fill={PINK} />
      ))}

      {AXES.map((ax) => {
        const score = Math.round(scores[ax.label] ?? 50);
        const [ix, iy] = pt(ax.angle, r + 40);
        let tx = ix, ty = iy;
        const anchor: 'start' | 'middle' | 'end' = 'middle';
        if (ax.labelPos === 'top') ty = iy - 4;
        else if (ax.labelPos === 'right') { tx = ix + 24; }
        else if (ax.labelPos === 'br') ty = iy + 6;
        else if (ax.labelPos === 'bl') ty = iy + 6;

        return (
          <g key={ax.id}>
            <image href={`/axis_icons/${ax.id}.png`} x={ix - 20} y={iy - 42} width={40} height={40} preserveAspectRatio="xMidYMid meet" />
            <text x={tx} y={ty + 6} textAnchor={anchor} fontSize={13} fill={PINK} fontWeight={900}>{ax.label}</text>
            <text x={tx} y={ty + 21} textAnchor={anchor} fontSize={8.5} fill="#AAAAAA">{ax.left} ← → {ax.right}</text>
            <text x={tx} y={ty + 52} textAnchor={anchor} fontSize={34} fill={PINK} fontWeight={900}>{score}</text>
            <text x={tx} y={ty + 68} textAnchor={anchor} fontSize={8} fill="#BBBBBB">(0 ← → 100)</text>
          </g>
        );
      })}
    </svg>
  );
}
