interface Props {
  count: number
}

export default function StickerWall({ count }: Props) {
  const stickers = Array.from({ length: count }, (_, i) => i)

  return (
    <div style={styles.container}>
      {stickers.map(i => (
        <span key={i} style={styles.star}>⭐</span>
      ))}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    padding: '0.5rem',
    justifyContent: 'center',
  },
  star: {
    fontSize: '1.2rem',
  },
}
