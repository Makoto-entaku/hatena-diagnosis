'use client';

import { useSearchParams } from 'next/navigation';
import type { ResultResponse } from '@/lib/types';
import PrintButton from './PrintButton';

const AXIS_ORDER = [
  { id: 'tolerance', label: '心の広さ度' },
  { id: 'social',    label: '社交度' },
  { id: 'action',    label: '怠惰度' },
  { id: 'logical',   label: 'ロジカル度' },
  { id: 'self',      label: '自分大切度' },
];

const RADAR_AXES = [
  { label: '心の広さ度', angle: -90 },
  { label: '社交度',     angle: -18 },
  { label: '怠惰度',     angle: 54 },
  { label: 'ロジカル度', angle: 126 },
  { label: '自分大切度', angle: 198 },
];

const PINK = '#E8769F';
const GRAY_NUM = '#C9C9C9';

// カード表示サイズ: 596x843 のPNGを 559x790 で表示（A5比率維持）
const CARD_W = 559;
const CARD_H = 790;

export default function ResultCard({ result }: { result: ResultResponse }) {
  const searchParams = useSearchParams();
  const station = Number(searchParams.get('station') ?? '1');

  // レーダー中心（確定）
  const RCENTER: [number, number] = [153, 475];
  // 各軸の「スコア100」の頂点座標。心の広さ(上)は確定済み(153,407)。
  // 他は正五角形RRAD=68の初期値。背景グリッドに合わせて1軸ずつ調整する。
  const AXIS_TIP: Record<string, [number, number]> = {
    '心の広さ度': [152, 410],
    '社交度':     [213, 455],
    '怠惰度':     [190, 525],
    'ロジカル度': [115, 525],
    '自分大切度': [92, 455],
  };
  // スコア0→中心, 100→頂点 で補間（50は自動的に中点）
  const tipPt = (label: string, ratio: number): [number, number] => {
    const [cx, cy] = RCENTER;
    const [tx, ty] = AXIS_TIP[label] ?? [cx, cy];
    return [cx + (tx - cx) * ratio, cy + (ty - cy) * ratio];
  };
  // スコア数字配置用のpt関数（従来通り）
  const RCX = 153, RCY = 475, RRAD = 68;

  const dataPts = RADAR_AXES.map((ax) => {
    const v = Math.min(Math.max(result.display_scores[ax.label] ?? 50, 0), 100) / 100;
    return tipPt(ax.label, v);
  });
  const dataPath = dataPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

  return (
    <div style={{ fontFamily: 'var(--font-source-han), sans-serif', backgroundColor: 'white', minHeight: '100vh', padding: 0 }}>
      <p style={{ fontSize: 10, color: '#666', textAlign: 'left', paddingLeft: 12, margin: '4px 0', fontWeight: 700 }}>
        はてな展｜診断結果
      </p>

      <article style={{ width: CARD_W, height: CARD_H, margin: '0 auto', position: 'relative', overflow: 'hidden' }}>
        {/* 背景PNG（デザイナーの骨格、淡ピンク地込み） */}
        <img src="/card_bg.png" alt="" style={{ position: 'absolute', top: 0, left: 0, width: CARD_W, height: CARD_H, zIndex: 0 }} />

        {/* ① ヘッダー: 白枠内（白枠 x≈98,y≈160,w≈400,h≈140） */}
        <div style={{ position: 'absolute', top: 180, left: 108, width: 250, zIndex: 2 }}>
          <p style={{ color: 'white', fontSize: 10, fontWeight: 700, margin: '0 0 2px' }}>{result.tagline}</p>
          <h2 style={{ color: 'white', fontWeight: 900, fontSize: 25, margin: '0 0 4px', lineHeight: 1.05, whiteSpace: 'nowrap' }}>
            {result.type_name}<span style={{ fontSize: 14, marginLeft: 4 }}>タイプ</span>
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.95)', fontSize: 9.5, margin: 0, lineHeight: 1.5 }}>{result.description}</p>
        </div>
        {/* ヘッダー右: イラスト */}
        <div style={{ position: 'absolute', top: 170, left: 360, width: 110, zIndex: 2 }}>
          <img src={'/type_images/' + result.type_id + '.png'} alt="" style={{ width: 110, height: 'auto', objectFit: 'contain' }} />
        </div>

        {/* ② レーダー データ五角形 */}
        <svg style={{ position: 'absolute', top: 0, left: 0, width: CARD_W, height: CARD_H, zIndex: 1, pointerEvents: 'none' }} viewBox={`0 0 ${CARD_W} ${CARD_H}`}>
          <path d={dataPath} fill="rgba(232,118,159,0.30)" stroke={PINK} strokeWidth={2} strokeLinejoin="round" />
          {dataPts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={3} fill={PINK} />)}
        </svg>
        {/* レーダー5スコア（軸の外側） */}
        {RADAR_AXES.map((ax) => {
          const sc = Math.round(result.display_scores[ax.label] ?? 50);
          // 参考デザインに合わせた絶対座標 [left, top]
          const posMap: Record<string, [number, number]> = {
            '心の広さ度': [183, 386],
            '社交度':     [252, 483],
            '怠惰度':     [185, 574],
            'ロジカル度': [83, 573],
            '自分大切度': [61, 447],
          };
          const [px, py] = posMap[ax.label] ?? [RCX, RCY];
          return (
            <div key={ax.label} style={{ position: 'absolute', left: px - 22, top: py - 14, width: 44, textAlign: 'center', zIndex: 2 }}>
              <span style={{ fontSize: 22, fontWeight: 900, color: PINK }}>{sc}</span>
            </div>
          );
        })}

        {/* ③ 来場者比較スコア（行 y起点≈345, 行高≈52） */}
        {AXIS_ORDER.map((axis, idx) => {
          const score = result.display_scores[axis.label] ?? 50;
          const diff = result.axis_comparisons?.[axis.id] ?? 0;
          const avg = Math.min(Math.max(Math.round(score - diff), 0), 100);
          const rowCenterY = 360 + idx * 53.5;
          return (
            <div key={axis.id} style={{ position: 'absolute', left: 445, top: rowCenterY - 16, zIndex: 2, display: 'flex', alignItems: 'center' }}>
              <span style={{ fontSize: 24, fontWeight: 900, color: PINK, width: 36, textAlign: 'right', marginLeft: -4 }}>{Math.round(score)}</span>
              <span style={{ fontSize: 16, fontWeight: 900, color: GRAY_NUM, width: 28, textAlign: 'center', marginLeft: 16 }}>{avg}</span>
            </div>
          );
        })}

        {/* ④ みんなと違う回答（枠 x≈98,y≈610,w≈115,h≈90） */}
        <div style={{ position: 'absolute', top: 633, left: 40, width: 136, zIndex: 2 }}>
          {result.weird_answers && result.weird_answers.length > 0 ? (
            result.weird_answers.slice(0, 3).map((w, i) => (
              <div key={i} style={{ fontSize: 8.5, color: '#555', marginBottom: 5, lineHeight: 1.4 }}>
                <span style={{ color: '#ff64a5', fontWeight: 700, fontSize: 6 }}>{w.question_summary}</span><br />
                <span style={{ color: '#ffadd0', fontSize: 6 }}>…{w.answer_label}（全体の{w.ratio}%）</span>
              </div>
            ))
          ) : (
            <p style={{ fontSize: 8.5, color: '#bbb', margin: 0 }}>データ蓄積中</p>
          )}
        </div>

        {/* ⑤ 性格診断3カラム（見出し下線の下に本文） */}
        {[
          { text: result.tendency, left: 225 },
          { text: result.suited, left: 320 },
          { text: result.strength, left: 415 },
        ].map((col, i) => (
          <div key={i} style={{ position: 'absolute', top: 638, left: col.left, width: 82, zIndex: 2 }}>
            <p style={{ fontSize: 7.5, color: '#555', lineHeight: 1.45, margin: 0 }}>{col.text}</p>
          </div>
        ))}
      </article>

      <div className="print-hidden" style={{ marginTop: 16, display: 'flex', justifyContent: 'center', paddingBottom: 16 }}>
        <PrintButton resultId={result.result_id} station={station} />
      </div>
      <p className="print-hidden" style={{ textAlign: 'center', fontSize: 9, color: '#ccc', paddingBottom: 8 }}>result_id: {result.result_id}</p>
    </div>
  );
}
