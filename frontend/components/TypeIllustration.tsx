interface Props {
  typeId: string;
  typeName: string;
  size?: number;
}

export default function TypeIllustration({ typeId, typeName, size = 160 }: Props) {
  return (
    <img
      src={`/types/${typeId}.png`}
      alt={typeName}
      width={size}
      height={size}
      style={{ objectFit: 'contain' }}
      className="print-keep-color"
    />
  );
}
