import { useEffect, useState } from 'react'

interface LessonSummary {
  id: number
  title: string
  cover: string | null
  page_count: number
}

interface Props {
  onSelect: (lesson: LessonSummary) => void
  onChallenge: () => void
}

export default function LessonPicker({ onSelect, onChallenge }: Props) {
  const [lessons, setLessons] = useState<LessonSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState<'home' | 'lessons'>('home')

  useEffect(() => {
    fetch('/api/lessons')
      .then(r => r.json())
      .then(data => { setLessons(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <div style={S.center}><div style={S.loadingText}>Loading...</div></div>
  }

  // Home: two mode cards
  if (mode === 'home') {
    return (
      <div style={S.center}>
        <div style={S.titleRow}>
          <span style={S.titleEmoji}>🐰 🐭</span>
          <h1 style={S.title}>Peppa Reader</h1>
          <span style={S.titleEmoji}>🐭 🐰</span>
        </div>
        <div style={S.subtitle}>Choose a mode to start</div>
        <div style={S.modeGrid}>
          <button style={S.modeCard} onClick={() => setMode('lessons')}>
            <div style={S.modeIcon}>📚</div>
            <div style={S.modeTitle}>Lesson</div>
            <div style={S.modeDesc}>Follow a lesson step by step</div>
          </button>
          <button style={{ ...S.modeCard, borderColor: '#f5b7b1', background: 'rgba(255,240,240,0.85)' }} onClick={onChallenge}>
            <div style={S.modeIcon}>⭐</div>
            <div style={{ ...S.modeTitle, color: '#c0392b' }}>Challenge</div>
            <div style={S.modeDesc}>Practice weak words</div>
          </button>
        </div>
        <button style={S.adminHint} onClick={() => {
          // trigger admin via parent
          window.dispatchEvent(new CustomEvent('open-admin'))
        }}>👨‍👩‍👧 Parent Panel</button>
      </div>
    )
  }

  // Lesson list
  return (
    <div style={S.listPage}>
      <button style={S.backBtnSmall} onClick={() => setMode('home')}>← 返回</button>
      <div style={S.listContent}>
        <h1 style={{ ...S.title, fontSize: '1.5rem', marginBottom: '1rem' }}>Choose a Lesson</h1>
        <div style={S.lessonGrid}>
          {lessons.map((lesson) => (
            <button key={lesson.id} style={S.lessonCard} onClick={() => onSelect(lesson)}>
              <div style={S.lessonImage}>
                {lesson.cover ? (
                  <img src={`/data/images/${lesson.cover}`} alt="" style={S.coverImg} />
                ) : (
                  <div style={S.coverPlaceholder}>📖</div>
                )}
              </div>
              <div style={S.lessonTitle}>{lesson.title}</div>
              <div style={S.lessonPages}>{lesson.page_count} pages</div>
            </button>
          ))}
          {lessons.length === 0 && <div style={S.empty}>No lessons yet. Create one in the parent panel.</div>}
        </div>
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  center: {
    width: '100%', height: '100%',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: '2rem', background: '#fdf6e8',
  },
  titleRow: {
    display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px',
  },
  titleEmoji: { fontSize: '1.5rem' },
  title: {
    fontSize: 'clamp(2rem, 5vw, 3rem)', fontWeight: 900,
    color: '#c8943e',
    textShadow: '1px 1px 0 rgba(255,255,255,0.8)',
  },
  subtitle: {
    fontSize: '1rem', color: '#b89a6a', marginBottom: '2.5rem',
  },
  modeGrid: {
    display: 'flex', gap: '2rem', flexWrap: 'wrap',
    justifyContent: 'center',
  },
  modeCard: {
    background: 'rgba(255,255,255,0.85)',
    border: '3px solid #e8dcc8',
    borderRadius: '24px', padding: '2rem 2.5rem',
    width: '240px', cursor: 'pointer',
    boxShadow: '0 6px 20px rgba(180,140,80,0.1)',
    transition: 'transform 0.2s, box-shadow 0.2s',
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    fontFamily: 'inherit', fontSize: 'inherit',
  },
  modeIcon: { fontSize: '3.5rem', marginBottom: '0.8rem' },
  modeTitle: { fontSize: '1.4rem', fontWeight: 800, color: '#5a3e1b', marginBottom: '0.4rem' },
  modeDesc: { fontSize: '0.9rem', color: '#b89a6a', textAlign: 'center' },

  adminHint: {
    marginTop: '2rem', padding: '8px 20px', borderRadius: 20,
    border: 'none', background: 'transparent',
    color: '#c4a87a', fontSize: '0.85rem', cursor: 'pointer',
    fontFamily: 'inherit', opacity: 0.6,
    transition: 'opacity 0.2s',
  },

  backBtnSmall: {
    position: 'fixed', top: 12, left: 12,
    padding: '6px 16px', borderRadius: 20,
    border: '2px solid #d4a574', background: 'rgba(255,255,255,0.7)',
    color: '#8b6914', fontSize: '0.95rem', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit', zIndex: 100,
  },
  listPage: {
    width: '100%', height: '100%',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', padding: '2rem', background: '#fdf6e8',
  },
  listContent: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', flex: 1,
  },
  lessonGrid: {
    display: 'flex', gap: '1.5rem', flexWrap: 'wrap',
    justifyContent: 'center', maxWidth: '900px', marginTop: '1.5rem',
  },
  lessonCard: {
    background: 'rgba(255,255,255,0.85)',
    border: '3px solid #e8dcc8',
    borderRadius: '24px', padding: '1rem',
    width: '220px', cursor: 'pointer',
    boxShadow: '0 6px 20px rgba(180,140,80,0.1)',
    transition: 'transform 0.2s, box-shadow 0.2s',
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    fontFamily: 'inherit', fontSize: 'inherit',
  },
  lessonImage: {
    width: '100%', height: '160px', borderRadius: '16px',
    overflow: 'hidden', background: '#f5edd6',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    marginBottom: '0.8rem',
  },
  coverImg: { width: '100%', height: '100%', objectFit: 'cover' },
  coverPlaceholder: { fontSize: '3.5rem', opacity: 0.4 },
  lessonTitle: {
    fontSize: '1.1rem', fontWeight: 700, color: '#5a3e1b',
    textAlign: 'center', marginBottom: '0.3rem',
  },
  lessonPages: { fontSize: '0.85rem', color: '#b89a6a' },
  empty: { fontSize: '1rem', color: '#b89a6a', textAlign: 'center', marginTop: '2rem' },
  loadingText: { fontSize: '1.5rem', color: '#d4a574' },
}
