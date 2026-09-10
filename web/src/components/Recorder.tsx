import { useRef, useState, useEffect } from 'react'

interface Props {
  onComplete: (blob: Blob) => void
}

// 检测是否支持 WebM 格式
function isWebMSupported(): boolean {
  if (typeof MediaRecorder === 'undefined') return false
  return MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
}

// 检测是否支持 MP4 格式
function isMP4Supported(): boolean {
  if (typeof MediaRecorder === 'undefined') return false
  return MediaRecorder.isTypeSupported('audio/mp4')
}

// 获取支持的 MIME 类型
function getSupportedMimeType(): string {
  if (isWebMSupported()) return 'audio/webm;codecs=opus'
  if (isMP4Supported()) return 'audio/mp4'
  return ''  // 浏览器会使用默认格式
}

export default function Recorder({ onComplete }: Props) {
  const [state, setState] = useState<'idle' | 'recording' | 'processing' | 'unsupported'>('idle')
  const [error, setError] = useState<string | null>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  // 检查浏览器支持
  useEffect(() => {
    if (typeof navigator === 'undefined') return
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setState('unsupported')
      setError('浏览器不支持录音（需要 HTTPS 或 localhost）')
      return
    }
    if (typeof MediaRecorder === 'undefined') {
      setState('unsupported')
      setError('浏览器不支持 MediaRecorder API')
      return
    }
  }, [])

  const startRecording = async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // 获取支持的 MIME 类型
      const mimeType = getSupportedMimeType()
      
      // 创建 MediaRecorder，如果 mimeType 为空则使用默认配置
      const recorderOptions: MediaRecorderOptions = {}
      if (mimeType) {
        recorderOptions.mimeType = mimeType
      }
      
      const recorder = new MediaRecorder(stream, recorderOptions)
      chunksRef.current = []
      
      recorder.ondataavailable = (e) => { 
        if (e.data.size > 0) chunksRef.current.push(e.data) 
      }
      
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        // 使用 recorder.mimeType 确保使用实际的格式
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        setState('processing')
        onComplete(blob)
        setTimeout(() => setState('idle'), 1500)
      }
      
      recorder.onerror = (e) => {
        console.error('MediaRecorder error:', e)
        stream.getTracks().forEach(t => t.stop())
        setError('录音出错，请重试')
        setState('idle')
      }
      
      mediaRef.current = recorder
      recorder.start()
      setState('recording')
    } catch (err: any) {
      console.error('Microphone access denied:', err)
      if (err.name === 'NotAllowedError') {
        setError('请允许麦克风访问权限')
      } else if (err.name === 'NotFoundError') {
        setError('未找到麦克风设备')
      } else {
        setError('无法访问麦克风：' + err.message)
      }
    }
  }

  const stopRecording = () => { mediaRef.current?.stop() }
  
  const handleClick = () => {
    if (state === 'idle') startRecording()
    else if (state === 'recording') stopRecording()
  }

  if (state === 'unsupported') {
    return (
      <div style={S.wrapper}>
        <div style={S.errorText}>{error || '浏览器不支持录音'}</div>
      </div>
    )
  }

  const label = state === 'recording' ? '⏹ Stop' : state === 'processing' ? '⏳ ...' : '🎤 朗读'

  return (
    <div style={S.wrapper}>
      {state === 'recording' && <style>{`@keyframes recPulse { 0%,100%{box-shadow:0 0 0 0 rgba(212,165,116,0.5)} 50%{box-shadow:0 0 0 12px rgba(212,165,116,0)} } .rec-pulse{animation:recPulse 1.2s infinite}`}</style>}
      {error && <div style={S.errorText}>{error}</div>}
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
  wrapper: { display: 'flex', alignItems: 'center', gap: 8 },
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
  errorText: {
    fontSize: '0.8rem',
    color: '#c0392b',
    textAlign: 'center',
  },
}
