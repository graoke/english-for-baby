import { useState, useEffect } from 'react'

interface Props {
  children: React.ReactNode
}

export default function AdminGuard({ children }: Props) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showPinInput, setShowPinInput] = useState(false)
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [isSettingPin, setIsSettingPin] = useState(false)

  useEffect(() => {
    // 检查是否已设置 PIN
    fetch('/api/settings/pin/status')
      .then(r => r.json())
      .then(data => {
        if (!data.has_pin) {
          // 未设置 PIN，进入设置模式
          setIsSettingPin(true)
          setShowPinInput(true)
        }
        setLoading(false)
      })
      .catch(() => {
        // 出错也允许进入（兼容旧版本）
        setIsAuthenticated(true)
        setLoading(false)
      })
  }, [])

  const handleSetPin = () => {
    if (pin.length < 4) {
      setError('PIN 至少 4 位')
      return
    }
    fetch('/api/settings/pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin })
    })
      .then(r => r.json())
      .then(() => {
        setIsAuthenticated(true)
      })
      .catch(() => setError('设置失败'))
  }

  const handleVerifyPin = () => {
    fetch('/api/settings/pin/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin })
    })
      .then(r => {
        if (r.ok) {
          setIsAuthenticated(true)
          setError('')
        } else {
          setError('PIN 错误')
        }
      })
      .catch(() => setError('验证失败'))
  }

  const handleLogout = () => {
    setIsAuthenticated(false)
    setShowPinInput(true)
    setPin('')
  }

  // 暴露 logout 方法给父组件
  useEffect(() => {
    ;(window as any).__peppaParentLogout = handleLogout
    return () => {
      delete (window as any).__peppaParentLogout
    }
  }, [])

  if (loading) {
    return (
      <div style={S.overlay}>
        <div style={S.card}>
          <div style={S.loading}>Loading...</div>
        </div>
      </div>
    )
  }

  if (isAuthenticated) {
    return <>{children}</>
  }

  return (
    <div style={S.overlay}>
      <div style={S.card}>
        <div style={S.icon}>🔒</div>
        <div style={S.title}>家长面板</div>
        {isSettingPin ? (
          <>
            <div style={S.hint}>首次使用，请设置 PIN</div>
            <input
              style={S.input}
              type="password"
              maxLength={8}
              value={pin}
              onChange={e => { setPin(e.target.value); setError('') }}
              placeholder="输入 PIN（至少 4 位）"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && handleSetPin()}
            />
            <button style={S.btn} onClick={handleSetPin}>确认</button>
          </>
        ) : (
          <>
            <div style={S.hint}>请输入 PIN 进入</div>
            <input
              style={S.input}
              type="password"
              maxLength={8}
              value={pin}
              onChange={e => { setPin(e.target.value); setError('') }}
              autoFocus
              onKeyDown={e => e.key === 'Enter' && handleVerifyPin()}
            />
            <button style={S.btn} onClick={handleVerifyPin}>进入</button>
          </>
        )}
        {error && <div style={S.error}>{error}</div>}
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(253,246,232,0.95)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000,
  },
  card: {
    background: 'white', borderRadius: 24, padding: '40px 48px',
    textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.1)',
    minWidth: 300,
  },
  icon: { fontSize: '3rem', marginBottom: 16 },
  title: { fontSize: '1.4rem', fontWeight: 900, color: '#c8943e', marginBottom: 8 },
  hint: { fontSize: '0.9rem', color: '#8b7355', marginBottom: 16 },
  input: {
    width: '100%', padding: '12px 16px', borderRadius: 12,
    border: '2px solid #e8dcc8', fontSize: '1.1rem', textAlign: 'center',
    fontFamily: 'inherit', marginBottom: 12, boxSizing: 'border-box',
  },
  error: { fontSize: '0.85rem', color: '#c0392b', marginTop: 8 },
  btn: {
    padding: '10px 32px', borderRadius: 20, border: 'none',
    background: '#d4a574', color: 'white', fontSize: '1rem', fontWeight: 700,
    cursor: 'pointer', fontFamily: 'inherit',
  },
  loading: {
    fontSize: '1rem', color: '#8b7355', padding: '20px',
  },
}
