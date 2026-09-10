import { useEffect, useRef, useState } from 'react'
import Confetti from './Confetti'
import { startRecording, uploadRecording } from '../utils/recording'

interface DrillItem {
  id: number; page_no: number; content_type: string
  text: string; text_zh: string | null; image_path: string | null
  tts_path: string | null; difficulty: number
}

interface Props {
  lessonId: number; lessonTitle: string; showText: boolean; onBack: () => void
}

export default function DrillPlayer({ lessonId, lessonTitle, showText, onBack }: Props) {
  const [items, setItems] = useState<DrillItem[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [stickerCount, setStickerCount] = useState(0)
  const [showConfetti, setShowConfetti] = useState(false)
  const [showFinish, setShowFinish] = useState(false)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Recording state
  const [recordingState, setRecordingState] = useState<'idle' | 'recording'>('idle')
  const [lastRecordingUrl, setLastRecordingUrl] = useState<string | null>(null)
  const [showPlayback, setShowPlayback] = useState(false)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const recordingItemRef = useRef<number | null>(null)

  const touchStartX = useRef(0)
  const touchStartY = useRef(0)

  // Cleanup object URLs to prevent memory leaks
  useEffect(() => {
    return () => { if (lastRecordingUrl) URL.revokeObjectURL(lastRecordingUrl) }
  }, [lastRecordingUrl])

  useEffect(() => {
    fetch(`/api/lessons/${lessonId}`)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(data => { setItems(data.items || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [lessonId])

  const currentItem = items[currentIndex]
  const totalPages = items.length
  const progress = totalPages > 0 ? ((currentIndex + 1) / totalPages) * 100 : 0

  const goNext = () => { if (currentIndex < items.length - 1) setCurrentIndex(currentIndex + 1); setShowPlayback(false); setLastRecordingUrl(null); setError(null) }
  const goPrev = () => { if (currentIndex > 0) setCurrentIndex(currentIndex - 1); setShowPlayback(false); setLastRecordingUrl(null); setError(null) }

  // TTS playback — auto-generate if missing
  const playTTS = async () => {
    if (!currentItem) return
    let path = currentItem.tts_path

    if (!path) {
      setGenerating(true)
      try {
        const res = await fetch(`/api/items/${currentItem.id}/generate-tts`, { method: 'POST' })
        const data = await res.json()
        if (data.ok && data.tts_path) {
          path = data.tts_path
          // Update local state
          setItems(prev => prev.map((it, i) => i === currentIndex ? { ...it, tts_path: path } : it))
        }
      } catch (e) {
        console.error('TTS generation failed:', e)
        setGenerating(false)
        return
      }
      setGenerating(false)
    }

    if (path) {
      const audio = new Audio(`/data/audio/${path}`)
      audio.play()
    }
  }

  const startRecording = async () => {
    try {
      setError(null)
      const result = await startRecording({
        onRecordingComplete: ({ blob, durationMs, mimeType }) => {
          setLastRecordingUrl(URL.createObjectURL(blob))
          setRecordingState('idle')
          setShowConfetti(true)
          setStickerCount(c => c + 1)
          setShowPlayback(true)
          setTimeout(() => setShowConfetti(false), 1500)
          const itemId = recordingItemRef.current
          if (itemId != null) uploadRecording(blob, itemId, durationMs, mimeType)
        },
        onError: (msg) => {
          setError(msg)
          setRecordingState('idle')
        },
      })
      if (!result) return
      mediaRef.current = result.recorder
      recordingItemRef.current = currentItem.id
      setRecordingState('recording')
      setShowPlayback(false)
    } catch (err: any) {
      console.error('Microphone access denied:', err)
      setError(err.name === 'NotAllowedError' ? '请允许麦克风访问权限' : '无法访问麦克风')
    }
  }

  const stopRecording = () => { mediaRef.current?.stop() }

  const playRecording = () => {
    if (lastRecordingUrl) {
      const audio = new Audio(lastRecordingUrl)
      audio.play()
    }
  }

  // Touch & keyboard
  const onTouchStart = (e: React.TouchEvent) => { touchStartX.current = e.touches[0].clientX; touchStartY.current = e.touches[0].clientY }
  const onTouchEnd = (e: React.TouchEvent) => {
    const dx = e.changedTouches[0].clientX - touchStartX.current
    const dy = e.changedTouches[0].clientY - touchStartY.current
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) { dx < 0 ? goNext() : goPrev() }
  }
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'ArrowRight') goNext(); if (e.key === 'ArrowLeft') goPrev() }
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h)
  })

  if (loading) return <div style={S.center}><div style={S.loadingText}>Loading...</div></div>
  if (!currentItem) return (
    <div style={S.center}>
      <div style={S.doneIcon}>🎉</div><div style={S.doneText}>All done!</div>
      <button style={S.backBtn} onClick={onBack}>Back to lessons</button>
    </div>
  )

  const recLabel = recordingState === 'recording' ? '⏹ Stop' : '🎤 朗读'

  return (
    <div style={S.root} onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      {showConfetti && <Confetti />}

      {/* Finish modal */}
      {showFinish && (
        <div style={S.modalOverlay}>
          <div style={S.modalCard}>
            <div style={S.modalStars}>⭐ 🌟 ⭐</div>
            <div style={S.modalTitle}>太棒了！</div>
            <div style={S.modalText}>你完成了「{lessonTitle}」</div>
            <div style={S.modalScore}>获得 ★ {stickerCount}</div>
            <button style={S.modalBtn} onClick={onBack}>确定</button>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={S.header}>
        <button style={S.backBtnSmall} onClick={onBack}>← 返回</button>
        <div style={S.headerTitle}>{lessonTitle}</div>
        <div style={S.headerRight}>★ {stickerCount}</div>
      </div>

      {/* Main card */}
      <div style={S.card}>
        <div style={showText ? S.cardLeft : S.cardLeftFull} onClick={playTTS}>
          {generating && <div style={S.genOverlay}>Generating...</div>}
          {currentItem.image_path ? (
            <img src={`/data/images/${currentItem.image_path}`} alt="" style={showText ? S.mainImage : S.mainImageLarge} />
          ) : (
            <div style={S.noImage}><div style={S.noImageEmoji}>📖</div></div>
          )}
        </div>
        {showText && (
          <div style={S.cardRight}>
            <div style={S.textLabel}>✨ Read with me</div>
            <div style={S.textCard}>
              <div style={S.englishText}>{currentItem.text}</div>
              {currentItem.text_zh && <div style={S.chineseText}>{currentItem.text_zh}</div>}
            </div>
            <div style={S.hintText} onClick={playTTS} role="button">
              {generating ? '⏳ generating audio...' : '🔊 tap to hear'}
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div style={S.errorBanner}>{error}</div>
      )}

      {/* Bottom bar */}
      <div style={S.bottomBar}>
        <button style={S.navBtn} onClick={goPrev} disabled={currentIndex === 0 || recordingState === 'recording'}>◀ 上一页</button>

        <div style={S.progressArea}>
          <span style={S.pageIndicator}>{currentIndex + 1} / {totalPages}</span>
          <div style={S.progressBar}><div style={{ ...S.progressFill, width: `${progress}%` }} /></div>
        </div>

        <button
          style={{ ...S.navBtn, ...(recordingState === 'recording' ? { opacity: 0.4, cursor: 'not-allowed' } : {}) }}
          onClick={currentIndex === totalPages - 1 ? () => setShowFinish(true) : goNext}
          disabled={recordingState === 'recording'}
        >
          {currentIndex === totalPages - 1 ? '完成 ✅' : '下一页 ▶'}
        </button>

        {/* Recording / Playback area */}
        <div style={S.recArea}>
          <button
            onClick={recordingState === 'recording' ? stopRecording : startRecording}
            style={{
              ...S.recBtn,
              ...(recordingState === 'recording' ? { background: '#c8943e', color: 'white', border: 'none' } : {}),
            }}
          >
            {recLabel}
          </button>

          {showPlayback && lastRecordingUrl && (
            <button style={S.playbackBtn} onClick={playRecording}>▶ 听我说的</button>
          )}
        </div>
      </div>

      <div style={S.footerHint}>提示: ← / → 翻页</div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  root: { width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: '#fdf6e8', overflow: 'hidden' },
  center: { width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#fdf6e8' },

  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', flexShrink: 0 },
  backBtnSmall: { padding: '6px 16px', borderRadius: 20, border: '2px solid #d4a574', background: 'rgba(255,255,255,0.7)', color: '#8b6914', fontSize: '0.95rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' },
  headerTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#8b6914' },
  headerRight: { fontSize: '1rem', fontWeight: 700, color: '#d4a574' },

  card: { flex: 1, display: 'flex', margin: '0 32px', borderRadius: 24, overflow: 'hidden', background: 'rgba(255,255,255,0.85)', boxShadow: '0 4px 20px rgba(180,140,80,0.12)', minHeight: 0 },
  cardLeft: { flex: '0 0 55%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5edd6', cursor: 'pointer', overflow: 'hidden', padding: 16, position: 'relative' },
  cardLeftFull: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5edd6', cursor: 'pointer', overflow: 'hidden', padding: 16, position: 'relative' },
  mainImage: { maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 16 },
  mainImageLarge: { maxWidth: '80%', maxHeight: '80%', objectFit: 'contain', borderRadius: 16 },
  noImage: { width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  noImageEmoji: { fontSize: '5rem', opacity: 0.3 },
  genOverlay: { position: 'absolute', inset: 0, background: 'rgba(255,255,255,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem', color: '#c8943e', fontWeight: 700, zIndex: 1 },
  cardRight: { flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '28px 32px', gap: 12 },
  textLabel: { fontSize: '1rem', color: '#c8943e', fontWeight: 700 },
  textCard: { background: 'rgba(255,240,200,0.6)', borderLeft: '4px solid #d4a574', borderRadius: 12, padding: '16px 20px' },
  englishText: { fontSize: 'clamp(1.3rem, 3vw, 2rem)', fontWeight: 700, color: '#5a3e1b', lineHeight: 1.5 },
  chineseText: { fontSize: '1rem', color: '#8b7355', marginTop: 8, lineHeight: 1.4 },
  hintText: { fontSize: '0.85rem', color: '#c4a87a', fontStyle: 'italic', cursor: 'pointer' },

  errorBanner: {
    textAlign: 'center', padding: '8px 16px', margin: '0 32px',
    background: '#fadbd8', color: '#c0392b', borderRadius: 12,
    fontSize: '0.85rem', fontWeight: 600,
  },

  bottomBar: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '10px 24px 6px', flexShrink: 0, flexWrap: 'wrap' },
  navBtn: { padding: '8px 18px', borderRadius: 20, border: '2px solid #d4a574', background: 'white', color: '#8b6914', fontSize: '0.9rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' },
  progressArea: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 100 },
  pageIndicator: { fontSize: '0.85rem', color: '#8b7355', fontWeight: 700 },
  progressBar: { width: '100%', height: 6, borderRadius: 3, background: '#e8dcc8', overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, #d4a574, #c8943e)', transition: 'width 0.3s ease' },

  recArea: { display: 'flex', alignItems: 'center', gap: 8 },
  recBtn: { padding: '8px 20px', borderRadius: 20, border: '2px solid #d4a574', background: 'white', color: '#8b6914', fontSize: '0.9rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap', transition: 'all 0.2s' },
  playbackBtn: { padding: '8px 16px', borderRadius: 20, border: '2px solid #87ceeb', background: 'white', color: '#2980b9', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' },

  footerHint: { textAlign: 'center', fontSize: '0.8rem', color: '#c4a87a', padding: '4px 0 10px', flexShrink: 0 },
  doneIcon: { fontSize: '5rem', marginBottom: '1rem' },
  doneText: { fontSize: '2rem', fontWeight: 700, color: '#d4a574', marginBottom: '1rem' },
  backBtn: { fontSize: '1rem', padding: '10px 28px', borderRadius: 25, border: 'none', background: '#d4a574', color: 'white', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 700 },
  loadingText: { fontSize: '1.5rem', color: '#d4a574' },

  modalOverlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
  },
  modalCard: {
    background: 'white', borderRadius: 24, padding: '32px 40px',
    textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.15)',
    minWidth: 280,
  },
  modalStars: { fontSize: '2.5rem', marginBottom: 12 },
  modalTitle: { fontSize: '1.6rem', fontWeight: 900, color: '#d4a574', marginBottom: 8 },
  modalText: { fontSize: '1rem', color: '#8b7355', marginBottom: 8 },
  modalScore: { fontSize: '1.2rem', fontWeight: 700, color: '#c8943e', marginBottom: 20 },
  modalBtn: {
    padding: '10px 36px', borderRadius: 25, border: 'none',
    background: '#d4a574', color: 'white', fontSize: '1rem', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
  },
}
