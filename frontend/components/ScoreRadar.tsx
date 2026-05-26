/**
 * 5軸スコア(0〜100)のレーダーチャート。
 *
 * 表示順: 社交度 / 心の広さ度 / 怠惰度 / 自分大切度 / ロジカル度
 *
 * `display_scores` をそのまま渡せば動作する(行動軸は backend 側で既に
 * 100-action へ反転済み)。
 */

interface Props {
  /** ラベル → スコア(0〜100) の連想。 */
  scores: Record<string, number>;
  /** 表示順。省略時はデフォルト5軸。 */
  order?: string[];
  /** SVG サイズ(正方形)。 */
  size?: number;
}

const DEFAULT_ORDER = ['社交度', '心の広さ度', '怠惰度', '自分大切度', 'ロジカル度'];

export default function ScoreRadar({
  scores,
  order = DEFAULT_ORDER,
  size = 320,
}: Props) {
  const labels = order;
  const n = labels.length;
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.38;

  // 各軸の方向ベクトル(上を 0°、時計回り)
  const angle = (i: number) => (i / n) * Math.PI * 2 - Math.PI / 2;

  // 軸線・グリッドの座標
  const axisPoints = labels.map((_, i) => ({
    x: cx + Math.cos(angle(i)) * radius,
    y: cy + Math.sin(angle(i)) * radius,
  }));

  // 同心五角形のグリッド(20/40/60/80/100)
  const grids = [0.2, 0.4, 0.6, 0.8, 1.0].map((r) =>
    labels
      .map((_, i) => {
        const x = cx + Math.cos(angle(i)) * radius * r;
        const y = cy + Math.sin(angle(i)) * radius * r;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' '),
  );

  // データポリゴン
  const dataPath = labels
    .map((label, i) => {
      const v = Math.max(0, Math.min(100, scores[label] ?? 0)) / 100;
      const x = cx + Math.cos(angle(i)) * radius * v;
      const y = cy + Math.sin(angle(i)) * radius * v;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  // ラベル位置(軸頂点の少し外側)
  const labelPositions = labels.map((_, i) => {
    const r = radius + 22;
    return {
      x: cx + Math.cos(angle(i)) * r,
      y: cy + Math.sin(angle(i)) * r,
    };
  });

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      role="img"
      aria-label="5軸スコアレーダーチャート"
      className="print-keep-color"
    >
      {/* グリッド */}
      {grids.map((points, i) => (
        <polygon
          key={i}
          points={points}
          fill="none"
          stroke="#c8c4b4"
          strokeWidth={i === grids.length - 1 ? 1.5 : 0.8}
        />
      ))}

      {/* 軸線 */}
      {axisPoints.map((p, i) => (
        <line
          key={i}
          x1={cx}
          y1={cy}
          x2={p.x}
          y2={p.y}
          stroke="#c8c4b4"
          strokeWidth={0.8}
        />
      ))}

      {/* データポリゴン */}
      <polygon
        points={dataPath}
        fill="#1f2c5b"
        fillOpacity={0.22}
        stroke="#1f2c5b"
        strokeWidth={2.2}
        strokeLinejoin="round"
      />

      {/* データ頂点ドット */}
      {labels.map((label, i) => {
        const v = Math.max(0, Math.min(100, scores[label] ?? 0)) / 100;
        const x = cx + Math.cos(angle(i)) * radius * v;
        const y = cy + Math.sin(angle(i)) * radius * v;
        return (
          <circle key={i} cx={x} cy={y} r={3.5} fill="#1f2c5b" />
        );
      })}

      {/* ラベル + 値 */}
      {labels.map((label, i) => {
        const p = labelPositions[i];
        const v = Math.round(scores[label] ?? 0);
        const anchor =
          Math.abs(p.x - cx) < 1 ? 'middle' : p.x < cx ? 'end' : 'start';
        return (
          <g key={i} fontFamily="inherit">
            <text
              x={p.x}
              y={p.y - 4}
              textAnchor={anchor}
              fontSize={12}
              fontWeight={700}
              fill="#1f2c5b"
            >
              {label}
            </text>
            <text
              x={p.x}
              y={p.y + 10}
              textAnchor={anchor}
              fontSize={11}
              fill="#1f2c5b"
              opacity={0.75}
            >
              {v}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
