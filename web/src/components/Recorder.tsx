import { useRef, useState } from 'react'

interface Props {
  onComplete: (blob: Blob) => void
}

export default function Recorder({ onComplete }: Props) {
  const [state, setState] = useState<'idle' | 'recording' | 'processing'>('idle')
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setState('processing')
        onComplete(blob)
        setTimeout(() => setState('idle'), 1500)
      }
      mediaRef.current = recorder
      recorder.start()
      setState('recording')
    } catch (err) {
      console.error('Microphone access denied:', err)
    }
  }

  const stopRecording = () => { mediaRef.current?.stop() }
  const handleClick = () => {
    if (state === 'idle') startRecording()
    else if (state === 'recording') stopRecording()
  }

  const label = state === 'recording' ? '⏹ Stop' : state === 'processing' ? '⏳ ...' : '🎤 朗读'

  return (
    <div style={S.wrapper}>
      {state === 'recording' && <style>{`@keyframes recPulse { 0%,100%{box-shadow:0 0 0 0 rgba(212,165,116,0.5)} 50%{box-shadow:0 0 0 12px rgba(212,165,116,0)} } .rec-pulse{animation:recPulse 1.2s infinite}`}</style>}
      <button
        onClick={handleClick}
        style={{
          ...S.button,
          ...(state === 'recording' ? { background: '#c8943e', color: 'white', border: 'none' } : {}),
          ...(state === 'processing' ? { opacity: 0.6 } : {}),
        }}
        className={state === 'recording' ? 'rec-pulse' : ''}
        disabled={state === 'processing'}
      >
        {label}
      </button>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  wrapper: { display: 'flex', alignItems: 'center' },
  button: {
    padding: '8px 22px',
    borderRadius: '20px',
    border: '2px solid #d4a574',
    background: 'white',
    color: '#8b6914',
    fontSize: '0.95rem',
    fontWeight: 700,
    cursor: 'pointer',
    fontFamily: 'inherit',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    whiteSpace: 'nowrap',
    transition: 'all 0.2s',
  },
}
