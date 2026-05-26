/**
 * 16タイプの動物イラスト プレースホルダ。
 *
 * 本番では各タイプの動物 SVG/PNG に差し替える(types.json の `id` をキーに
 * /public/types/{id}.svg を読み込む形にすると差し替えやすい)。現状は
 * type_id の頭文字を使った汎用バッジ風 SVG を返す。
 */

interface Props {
  typeId: string;     // "sloth" / "dolphin" 等
  typeName: string;   // "お人よしナマケモノ" 等
  size?: number;      // px
}

const COLOR_BY_ID: Record<string, [string, string]> = {
  dolphin:  ['#7cc7ff', '#2575c6'],
  golden:   ['#ffd66e', '#d8881f'],
  capybara: ['#caa57a', '#7d5a35'],
  panda:    ['#f0f0f0', '#2b2b2b'],
  lion:     ['#ffba6b', '#b25b0e'],
  bee:      ['#ffe066', '#8a6500'],
  hippo:    ['#b18ec9', '#5e3a85'],
  penguin:  ['#88a6c4', '#243d5f'],
  stray_cat:['#dccfb6', '#6b5a3f'],
  beaver:   ['#c08a55', '#5e3717'],
  sloth:    ['#a99877', '#5c4a2a'],
  koala:    ['#b8c1c4', '#4b585c'],
  wolf:     ['#9aa6b2', '#3c4855'],
  shepherd: ['#a87a5b', '#3e2516'],
  leopard:  ['#e8c97c', '#7a5410'],
  hedgehog: ['#c8b48c', '#5c4624'],
};

export default function TypeIllustration({ typeId, typeName, size = 160 }: Props) {
  const [bg, fg] = COLOR_BY_ID[typeId] || ['#dcdcdc', '#444'];
  const initials = (typeName || typeId || '?').slice(0, 1);

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 200"
      width={size}
      height={size}
      role="img"
      aria-label={typeName}
      className="print-keep-color"
    >
      <defs>
        <radialGradient id={`g-${typeId}`} cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor={bg} stopOpacity="1" />
          <stop offset="100%" stopColor={fg} stopOpacity="0.85" />
        </radialGradient>
      </defs>
      <circle cx="100" cy="100" r="92" fill={`url(#g-${typeId})`} stroke={fg} strokeWidth="3" />
      <text
        x="100"
        y="115"
        textAnchor="middle"
        fontSize="78"
        fontWeight="700"
        fill="#fff"
        style={{ paintOrder: 'stroke', stroke: fg, strokeWidth: 4 }}
      >
        {initials}
      </text>
    </svg>
  );
}
