import { useState, useEffect } from 'react'

const TOKEN_KEY = 'peppa_session_token'

interface Props {
  children: React.ReactNode
}

function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

function setToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

export function getSessionToken(): string | null {
  return getToken()
}

async function sha256(msg: string): Promise<string> {
  const data = new TextEncoder().encode(msg)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('')
}

export default function AdminGuard({ children }: Props) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showPinInput, setShowPinInput] = useState(false)
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [isSettingPin, setIsSettingPin] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (token) {
      fetch('/api/settings', {
        headers: { 'X-Session-Token': token }
      }).then(r => {
        if (r.ok) setIsAuthenticated(true)
        else { clearToken(); checkPinStatus() }
        setLoading(false)
      }).catch(() => setLoading(false))
    } else {
      checkPinStatus()
    }
  }, [])

  const checkPinStatus = () => {
    fetch('/api/settings/pin/status')
      .then(r => r.json())
      .then(data => {
        setIsSettingPin(!data.has_pin)
        setShowPinInput(true)
        setLoading(false)
      })
      .catch(() => { setIsAuthenticated(true); setLoading(false) })
  }

  const handleSetPin = async () => {
    if (pin.length < 4) { setError('PIN 至少 4 位'); return }
    try {
      const res = await fetch('/api/settings/pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
      })
      if (!res.ok) throw new Error((await res.json()).detail || '设置失败')
      const data = await res.json()
      if (data.token) setToken(data.token)
      setIsAuthenticated(true)
    } catch (e: any) { setError(e.message) }
  }

  const handleVerifyPin = async () => {
    try {
      // 1. 获取 challenge + salt
      const challengeRes = await fetch('/api/settings/pin/challenge', { method: 'POST' })
      if (!challengeRes.ok) throw new Error('认证失败')
      const { challenge, salt } = await challengeRes.json()

      // 2. 计算 proof: h = sha256(challenge + sha256(salt + pin))
      const hashPin = await sha256(salt + pin)
      const h = await sha256(challenge + hashPin)

      // 3. 发送 proof
      const verifyRes = await fetch('/api/settings/pin/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge, h })
      })

      if (!verifyRes.ok) {
        if (verifyRes.status === 429) throw new Error('尝试次数过多，请稍后再试')
        throw new Error('PIN 错误')
      }

      const data = await verifyRes.json()
      if (data.token) setToken(data.token)
      setIsAuthenticated(true)
      setError('')
    } catch (e: any) { setError(e.message) }
  }

  const handleLogout = () => {
    const token = getToken()
    if (token) {
      fetch('/api/settings/pin/logout', {
        method: 'POST',
        headers: { 'X-Session-Token': token }
      }).catch(() => {})
    }
    clearToken()
    setIsAuthenticated(false)
    setShowPinInput(true)
    setPin('')
  }

  useEffect(() => {
    ;(window as any).__peppaParentLogout = handleLogout
    return () => { delete (window as any).__peppaParentLogout }
  }, [])

  if (loading) return <div style={S.overlay}><div style={S.card}><div style={S.loading}>Loading...</div></div></div>
  if (isAuthenticated) return <>{children}</>

  return (
    <div style={S.overlay}>
      <div style={S.card}>
        <div style={S.icon}>🔒</div>
        <div style={S.title}>家长面板</div>
        {isSettingPin ? (
          <>
            <div style={S.hint}>首次使用，请设置 PIN</div>
            <input style={S.input} type="password" maxLength={8} value={pin}
              onChange={e => { setPin(e.target.value); setError('') }}
              placeholder="输入 PIN（至少 4 位）" autoFocus
              onKeyDown={e => e.key === 'Enter' && handleSetPin()} />
            <button style={S.btn} onClick={handleSetPin}>确认</button>
          </>
        ) : (
          <>
            <div style={S.hint}>请输入 PIN 进入</div>
            <input style={S.input} type="password" maxLength={8} value={pin}
              onChange={e => { setPin(e.target.value); setError('') }} autoFocus
              onKeyDown={e => e.key === 'Enter' && handleVerifyPin()} />
            <button style={S.btn} onClick={handleVerifyPin}>进入</button>
          </>
        )}
        {error && <div style={S.error}>{error}</div>}
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(253,246,232,0.95)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  card: { background: 'white', borderRadius: 24, padding: '40px 48px', textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.1)', minWidth: 300 },
  icon: { fontSize: '3rem', marginBottom: 16 },
  title: { fontSize: '1.4rem', fontWeight: 900, color: '#c8943e', marginBottom: 8 },
  hint: { fontSize: '0.9rem', color: '#8b7355', marginBottom: 16 },
  input: { width: '100%', padding: '12px 16px', borderRadius: 12, border: '2px solid #e8dcc8', fontSize: '1.1rem', textAlign: 'center', fontFamily: 'inherit', marginBottom: 12, boxSizing: 'border-box' },
  error: { fontSize: '0.85rem', color: '#c0392b', marginTop: 8 },
  btn: { padding: '10px 32px', borderRadius: 20, border: 'none', background: '#d4a574', color: 'white', fontSize: '1rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' },
  loading: { fontSize: '1rem', color: '#8b7355', padding: '20px' },
}
