import { useEffect, useState } from 'react'

interface Particle {
  id: number; x: number; y: number; color: string
  size: number; speedX: number; speedY: number; rotation: number; life: number
}

const COLORS = ['#d4a574', '#c8943e', '#87ceeb', '#98fb98', '#ffb347', '#ff69b4', '#fffacd']

export default function Confetti() {
  const [particles, setParticles] = useState<Particle[]>([])

  useEffect(() => {
    setParticles(Array.from({ length: 50 }, (_, i) => ({
      id: i, x: 50 + (Math.random() - 0.5) * 30, y: 40,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      size: 6 + Math.random() * 8,
      speedX: (Math.random() - 0.5) * 4, speedY: -3 - Math.random() * 5,
      rotation: Math.random() * 360, life: 1,
    })))
  }, [])

  useEffect(() => {
    const iv = setInterval(() => {
      setParticles(prev => prev.map(p => ({
        ...p, x: p.x + p.speedX, y: p.y + p.speedY,
        speedY: p.speedY + 0.15, rotation: p.rotation + 5, life: p.life - 0.02,
      })).filter(p => p.life > 0))
    }, 16)
    return () => clearInterval(iv)
  }, [])

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 9999, pointerEvents: 'none' }}>
      {particles.map(p => (
        <div key={p.id} style={{
          position: 'absolute', left: `${p.x}%`, top: `${p.y}%`,
          width: p.size, height: p.size, background: p.color,
          borderRadius: p.id % 2 === 0 ? '50%' : '2px',
          opacity: p.life, transform: `rotate(${p.rotation}deg)`,
        }} />
      ))}
      <div style={{
        position: 'absolute', top: '45%', left: '50%',
        transform: 'translate(-50%, -50%)', fontSize: '5rem',
      }}>🎉</div>
    </div>
  )
}
