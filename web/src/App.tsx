import { useEffect, useState } from 'react'
import LessonPicker from './components/LessonPicker'
import DrillPlayer from './components/DrillPlayer'
import Challenge from './components/Challenge'
import Admin from './pages/Admin'

type Screen = 'picker' | 'practice' | 'challenge' | 'admin'

interface LessonSummary { id: number; title: string; cover: string | null; page_count: number }

export interface AppSettings {
  show_text: boolean
}

const DEFAULT_SETTINGS: AppSettings = { show_text: true }

export default function App() {
  const [screen, setScreen] = useState<Screen>('picker')
  const [currentLesson, setCurrentLesson] = useState<LessonSummary | null>(null)
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS)

  // Load settings
  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => {
        setSettings({
          show_text: data.show_text !== 'false',
        })
      })
      .catch(() => {})
  }, [])

  // Listen for open-admin event from LessonPicker
  useEffect(() => {
    const handler = () => setScreen('admin')
    window.addEventListener('open-admin', handler)
    return () => window.removeEventListener('open-admin', handler)
  }, [])

  const updateSettings = (patch: Partial<AppSettings>) => {
    setSettings(prev => ({ ...prev, ...patch }))
    const body: Record<string, string> = {}
    if (patch.show_text !== undefined) body.show_text = patch.show_text ? 'true' : 'false'
    fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      {screen !== 'admin' && (
        <button onClick={() => setScreen('admin')} style={S.adminLink}>👨‍👩‍👧</button>
      )}

      {screen === 'admin' && (
        <div>
          <button onClick={() => setScreen('picker')} style={S.backLink}>← Back</button>
          <Admin settings={settings} onUpdateSettings={updateSettings} />
        </div>
      )}

      {screen === 'picker' && (
        <LessonPicker
          onSelect={(l) => { setCurrentLesson(l); setScreen('practice') }}
          onChallenge={() => setScreen('challenge')}
        />
      )}

      {screen === 'practice' && currentLesson && (
        <DrillPlayer
          lessonId={currentLesson.id}
          lessonTitle={currentLesson.title}
          showText={settings.show_text}
          onBack={() => setScreen('picker')}
        />
      )}

      {screen === 'challenge' && (
        <Challenge showText={settings.show_text} onBack={() => setScreen('picker')} />
      )}
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  adminLink: {
    position: 'fixed', top: 12, right: 12,
    width: 36, height: 36, borderRadius: '50%',
    border: 'none', background: 'rgba(255,255,255,0.5)',
    fontSize: '1.1rem', cursor: 'pointer', zIndex: 100,
    opacity: 0.4, transition: 'opacity 0.2s',
  },
  backLink: {
    position: 'fixed', top: 12, left: 12,
    padding: '6px 16px', borderRadius: 20,
    border: '2px solid #d4a574', background: 'rgba(255,255,255,0.7)',
    color: '#8b6914', fontSize: '0.9rem', fontWeight: 700,
    cursor: 'pointer', zIndex: 100, fontFamily: 'inherit',
  },
}
