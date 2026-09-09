import { useState, useEffect } from 'react'
import type { AppSettings } from '../App'

type Tab = 'list' | 'edit' | 'history' | 'weak' | 'settings'

interface AdminProps {
  settings: AppSettings
  onUpdateSettings: (patch: Partial<AppSettings>) => void
}

export default function Admin({ settings, onUpdateSettings }: AdminProps) {
  const [tab, setTab] = useState<Tab>('list')
  const [editingId, setEditingId] = useState<number | null>(null)

  return (
    <div style={S.page}>
      <h1 style={S.pageTitle}>👨‍👩‍👧 Parent Panel</h1>
      <div style={S.tabBar}>
        <button style={{ ...S.tab, ...(tab === 'list' ? S.tabActive : {}) }} onClick={() => setTab('list')}>Lessons</button>
        <button style={{ ...S.tab, ...(tab === 'history' ? S.tabActive : {}) }} onClick={() => setTab('history')}>History</button>
        <button style={{ ...S.tab, ...(tab === 'weak' ? S.tabActive : {}) }} onClick={() => setTab('weak')}>Weak Words</button>
        <button style={{ ...S.tab, ...(tab === 'settings' ? S.tabActive : {}) }} onClick={() => setTab('settings')}>Settings</button>
      </div>
      {tab === 'list' && <LessonList onEdit={(id) => { setEditingId(id); setTab('edit') }} onCreate={() => { setEditingId(null); setTab('edit') }} />}
      {tab === 'edit' && <LessonEditor lessonId={editingId} onDone={() => { setTab('list'); setEditingId(null) }} />}
      {tab === 'history' && <PracticeHistory />}
      {tab === 'weak' && <WeakSentences />}
      {tab === 'settings' && <AppSettingsPanel settings={settings} onUpdate={onUpdateSettings} />}
    </div>
  )
}

/* ==================== Settings Panel ==================== */
function AppSettingsPanel({ settings, onUpdate }: { settings: AppSettings; onUpdate: (p: Partial<AppSettings>) => void }) {
  const [checked, setChecked] = useState(settings.show_text)
  const toggle = () => {
    const next = !checked
    setChecked(next)
    onUpdate({ show_text: next })
  }
  return (
    <div>
      <div style={S.listTitle}>Display Settings</div>
      <div style={S.settingRow}>
        <div>
          <div style={S.settingLabel}>Show text in practice</div>
          <div style={S.settingHint}>If off, only image is shown (text hidden)</div>
        </div>
        <div
          onClick={toggle}
          style={{
            width: 48, height: 26, borderRadius: 13, cursor: 'pointer',
            background: checked ? '#d4a574' : '#e8dcc8',
            position: 'relative', transition: 'background 0.3s', flexShrink: 0,
          }}
        >
          <div style={{
            width: 20, height: 20, borderRadius: '50%', background: 'white',
            position: 'absolute', top: 3,
            left: checked ? 25 : 3,
            transition: 'left 0.3s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          }} />
        </div>
      </div>
    </div>
  )
}

/* ==================== Lesson List ==================== */
function LessonList({ onEdit, onCreate }: { onEdit: (id: number) => void; onCreate: () => void }) {
  const [lessons, setLessons] = useState<any[]>([])
  const [loaded, setLoaded] = useState(false)
  const load = () => fetch('/api/lessons').then(r => r.json()).then(d => { setLessons(d); setLoaded(true) })
  useEffect(() => { if (!loaded) load() }, [])
  return (
    <div>
      <div style={S.listHeader}>
        <span style={S.listTitle}>Lessons</span>
        <button style={S.primaryBtn} onClick={onCreate}>+ New</button>
      </div>
      {lessons.map(l => (
        <div key={l.id} style={S.listItem}>
          <div><div style={S.listItemTitle}>{l.title}</div><div style={S.listItemMeta}>{l.page_count} pages</div></div>
          <button style={S.editBtn} onClick={() => onEdit(l.id)}>Edit</button>
        </div>
      ))}
      {lessons.length === 0 && loaded && <div style={S.empty}>No lessons yet.</div>}
    </div>
  )
}

/* ==================== Lesson Editor ==================== */
interface ItemDraft { id: number | null; text: string; text_zh: string; image_path: string | null; tts_path: string | null; content_type: string; _removed?: boolean; _ttsLoading?: boolean }

function LessonEditor({ lessonId, onDone }: { lessonId: number | null; onDone: () => void }) {
  const [title, setTitle] = useState('')
  const [items, setItems] = useState<ItemDraft[]>([])
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [generatingTts, setGeneratingTts] = useState(false)

  useEffect(() => {
    if (lessonId) {
      fetch(`/api/lessons/${lessonId}`).then(r => r.json()).then(data => {
        setTitle(data.title)
        setItems((data.items || []).map((i: any) => ({ id: i.id, text: i.text, text_zh: i.text_zh || '', image_path: i.image_path, tts_path: i.tts_path, content_type: i.content_type || 'sentence' })))
        setLoaded(true)
      })
    } else { setLoaded(true) }
  }, [lessonId])

  const addItem = () => setItems(prev => [...prev, { id: null, text: '', text_zh: '', image_path: null, tts_path: null, content_type: 'sentence' }])
  const removeItem = (idx: number) => setItems(prev => prev.map((item, i) => i === idx ? { ...item, _removed: true } : item))
  const updateItem = (idx: number, field: string, value: any) => setItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item))

  const uploadImage = async (idx: number, file: File) => {
    const fd = new FormData(); fd.append('file', file)
    const res = await fetch('/api/upload/image', { method: 'POST', body: fd })
    const data = await res.json()
    updateItem(idx, 'image_path', data.filename)
  }

  const playItemTts = (item: ItemDraft) => {
    if (item.tts_path) { new Audio(`/data/audio/${item.tts_path}`).play() }
  }

  const regenerateItemTts = async (idx: number, item: ItemDraft) => {
    if (!item.id) return
    updateItem(idx, '_ttsLoading' as any, true)
    try {
      await fetch(`/api/items/${item.id}/generate-tts`, { method: 'POST' })
      // Re-fetch item to get new tts_path
      const res = await fetch(`/api/lessons/${lessonId}`)
      const data = await res.json()
      const updated = data.items?.find((i: any) => i.id === item.id)
      if (updated) updateItem(idx, 'tts_path', updated.tts_path)
      setStatus(`TTS regenerated for "${item.text.slice(0, 20)}..."`)
    } catch (e) { setStatus('TTS regeneration failed.') }
    updateItem(idx, '_ttsLoading' as any, false)
  }

  const handleSave = async () => {
    if (!title.trim()) { setStatus('Please enter a lesson title.'); return }
    setSaving(true); setStatus('')
    try {
      let lid = lessonId
      if (lid) {
        await fetch(`/api/lessons/${lid}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }) })
      } else {
        const res = await fetch('/api/lessons', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }) })
        const data = await res.json(); lid = data.id
      }
      const visible = items.filter(i => !i._removed)
      for (let idx = 0; idx < visible.length; idx++) {
        const item = visible[idx]
        const body = { text: item.text, text_zh: item.text_zh || null, image_path: item.image_path, content_type: item.content_type, page_no: idx + 1, source_type: 'manual', lesson_id: lid }
        if (item.id) { await fetch(`/api/items/${item.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) }
        else { await fetch('/api/items', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) }
      }
      for (const item of items.filter(i => i._removed && i.id)) { await fetch(`/api/items/${item.id}`, { method: 'DELETE' }) }
      if (lid) { await fetch(`/api/lessons/${lid}/recount`, { method: 'POST' }) }
      setStatus('Saved!'); setTimeout(() => onDone(), 800)
    } catch (e) { setStatus('Save failed: ' + String(e)) } finally { setSaving(false) }
  }

  const handleGenerateTts = async () => {
    if (!lessonId) return
    setGeneratingTts(true)
    try {
      const res = await fetch(`/api/items/lesson/${lessonId}/generate-tts`, { method: 'POST' })
      const data = await res.json()
      setStatus(`Generated TTS for ${data.generated} items.`)
      // Refresh items
      const lr = await fetch(`/api/lessons/${lessonId}`)
      const ld = await lr.json()
      setItems((ld.items || []).map((i: any) => ({ id: i.id, text: i.text, text_zh: i.text_zh || '', image_path: i.image_path, tts_path: i.tts_path, content_type: i.content_type || 'sentence' })))
    } catch (e) { setStatus('TTS generation failed.') }
    setGeneratingTts(false)
  }

  if (!loaded) return <div style={S.loading}>Loading...</div>
  const visibleItems = items.filter(i => !i._removed)

  return (
    <div>
      <div style={S.editorHeader}>
        <button style={S.secondaryBtn} onClick={onDone}>← Back</button>
        <span style={S.editorTitle}>{lessonId ? 'Edit Lesson' : 'New Lesson'}</span>
        <div style={{ display: 'flex', gap: 8 }}>
          {lessonId && <button style={S.ttsBtn} onClick={handleGenerateTts} disabled={generatingTts}>{generatingTts ? '⏳...' : '🔊 TTS All'}</button>}
          <button style={S.primaryBtn} onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        </div>
      </div>
      {status && <div style={{ ...S.status, color: status.includes('fail') ? '#c0392b' : '#27ae60' }}>{status}</div>}
      <div style={S.fieldGroup}>
        <label style={S.label}>Lesson Title</label>
        <input style={S.input} value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Animals" />
      </div>
      <div style={S.itemsSection}>
        <div style={S.itemsHeader}>
          <span style={S.itemsLabel}>Items ({visibleItems.length})</span>
          <button style={S.addBtn} onClick={addItem}>+ Add Item</button>
        </div>
        {visibleItems.map((item, idx) => {
          const realIdx = items.indexOf(item)
          return (
            <div key={realIdx} style={S.itemCard}>
              <div style={S.itemNumber}>{idx + 1}</div>
              <div style={S.itemContent}>
                {/* Image */}
                <div style={S.imageArea}>
                  {item.image_path ? (
                    <div style={S.imagePreview}>
                      <img src={`/data/images/${item.image_path}`} alt="" style={S.previewImg} />
                      <button style={S.removeImgBtn} onClick={() => updateItem(realIdx, 'image_path', null)}>×</button>
                    </div>
                  ) : (
                    <label style={S.uploadLabel}>
                      <input type="file" accept="image/*" style={{ display: 'none' }} onChange={e => { if (e.target.files?.[0]) uploadImage(realIdx, e.target.files[0]) }} />
                      <div style={S.uploadPlaceholder}><div style={S.uploadIcon}>🖼️</div><div style={S.uploadText}>Image</div></div>
                    </label>
                  )}
                </div>
                {/* Text fields + TTS */}
                <div style={S.textFields}>
                  <input style={S.itemInput} value={item.text} onChange={e => updateItem(realIdx, 'text', e.target.value)} placeholder="English text" />
                  <input style={{ ...S.itemInput, color: '#8b7355', fontSize: '0.8rem' }} value={item.text_zh} onChange={e => updateItem(realIdx, 'text_zh', e.target.value)} placeholder="Chinese (optional)" />
                  {/* TTS row */}
                  {item.id && (
                    <div style={S.ttsRow}>
                      <button style={S.ttsPlayBtn} onClick={() => playItemTts(item)} disabled={!item.tts_path} title="Play TTS">
                        {item.tts_path ? '▶' : '—'}
                      </button>
                      <button style={S.ttsRegenBtn} onClick={() => regenerateItemTts(realIdx, item)} disabled={!!(item as any)._ttsLoading} title="Regenerate TTS">
                        {(item as any)._ttsLoading ? '⏳' : '🔄'}
                      </button>
                      <span style={{ fontSize: '0.7rem', color: '#b89a6a' }}>{item.tts_path ? 'TTS ready' : 'No TTS'}</span>
                    </div>
                  )}
                </div>
              </div>
              <button style={S.removeBtn} onClick={() => removeItem(realIdx)} title="Remove">−</button>
            </div>
          )
        })}
        {visibleItems.length === 0 && <div style={S.emptyItems}>No items yet.</div>}
      </div>
    </div>
  )
}

/* ==================== Practice History ==================== */
function PracticeHistory() {
  const [daily, setDaily] = useState<any[]>([])
  const [loaded, setLoaded] = useState(false)

  // Default: last 7 days
  const today = new Date()
  const weekAgo = new Date(); weekAgo.setDate(weekAgo.getDate() - 6)
  const [startDate, setStartDate] = useState(weekAgo.toISOString().slice(0, 10))
  const [endDate, setEndDate] = useState(today.toISOString().slice(0, 10))

  useEffect(() => {
    fetch('/api/history/daily').then(r => r.json()).then(d => { setDaily(d); setLoaded(true) })
  }, [])

  const filtered = daily.filter(d => d.date >= startDate && d.date <= endDate)

  // Chart dimensions
  const W = 600, H = 220, PAD_L = 45, PAD_R = 45, PAD_B = 30, PAD_T = 20
  const plotW = W - PAD_L - PAD_R
  const plotH = H - PAD_T - PAD_B

  const maxCount = Math.max(1, ...filtered.map(d => d.sentence_count))
  const scoreTicks = [0, 50, 100]
  const countTicks = [0, Math.ceil(maxCount / 2), maxCount]

  // Build points
  const buildPoints = (valFn: (d: any) => number, max: number) => filtered.map((d, i) => ({
    x: PAD_L + (filtered.length === 1 ? plotW / 2 : (i / (filtered.length - 1)) * plotW),
    y: PAD_T + plotH - (valFn(d) / max) * plotH,
    raw: valFn(d),
    date: d.date,
  }))

  const countPoints = buildPoints(d => d.sentence_count, maxCount)
  const scorePoints = buildPoints(d => (d.avg_score ?? 0) * 100, 100)

  const countPath = countPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  const scorePath = scorePoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')

  return (
    <div>
      <div style={S.chartSection}>
        <div style={S.chartHeader}>
          <div style={S.chartTitle}>Daily Practice</div>
          <div style={S.dateSelect}>
            <input type="date" style={S.dateInput} value={startDate} onChange={e => setStartDate(e.target.value)} />
            <span style={{ color: '#b89a6a', fontSize: '0.85rem' }}>~</span>
            <input type="date" style={S.dateInput} value={endDate} onChange={e => setEndDate(e.target.value)} />
          </div>
        </div>
        {filtered.length === 0 && loaded && <div style={S.empty}>No practice data in this range.</div>}
        {filtered.length > 0 && (
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
            {/* Left Y-axis (count) */}
            {countTicks.map(v => {
              const y = PAD_T + plotH - (v / maxCount) * plotH
              return (
                <g key={`cl${v}`}>
                  <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y} stroke="#e8dcc8" strokeWidth="1" strokeDasharray={v === 0 ? '0' : '4,4'} />
                  <text x={PAD_L - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#c8943e" fontWeight="600">{v}</text>
                </g>
              )
            })}
            <text x={8} y={PAD_T + plotH / 2} textAnchor="middle" fontSize="9" fill="#c8943e" fontWeight="700"
              transform={`rotate(-90, 8, ${PAD_T + plotH / 2})`}>Count</text>

            {/* Right Y-axis (score) */}
            {scoreTicks.map(v => {
              const y = PAD_T + plotH - (v / 100) * plotH
              return (
                <g key={`sr${v}`}>
                  <text x={W - PAD_R + 6} y={y + 4} textAnchor="start" fontSize="10" fill="#27ae60" fontWeight="600">{v}%</text>
                </g>
              )
            })}
            <text x={W - 6} y={PAD_T + plotH / 2} textAnchor="middle" fontSize="9" fill="#27ae60" fontWeight="700"
              transform={`rotate(90, ${W - 6}, ${PAD_T + plotH / 2})`}>Score</text>

            {/* X-axis labels */}
            {countPoints.map((p, i) => (
              <text key={i} x={p.x} y={H - 6} textAnchor="middle" fontSize="9" fill="#b89a6a">
                {p.date.slice(5)}
              </text>
            ))}

            {/* Score line (green) */}
            {scorePoints.length > 1 && (
              <path d={scorePath} fill="none" stroke="#27ae60" strokeWidth="2" strokeLinejoin="round" />
            )}
            {scorePoints.map((p, i) => (
              <g key={`s${i}`}>
                <circle cx={p.x} cy={p.y} r="4" fill="white" stroke="#27ae60" strokeWidth="2" />
                <text x={p.x} y={p.y - 8} textAnchor="middle" fontSize="9" fill="#27ae60" fontWeight="700">
                  {p.raw.toFixed(0)}%
                </text>
              </g>
            ))}

            {/* Count line (orange) */}
            {countPoints.length > 1 && (
              <path d={countPath} fill="none" stroke="#d4a574" strokeWidth="2" strokeLinejoin="round" />
            )}
            {countPoints.map((p, i) => (
              <g key={`c${i}`}>
                <circle cx={p.x} cy={p.y} r="4" fill="white" stroke="#d4a574" strokeWidth="2" />
                <text x={p.x} y={p.y - 8} textAnchor="middle" fontSize="9" fill="#c8943e" fontWeight="700">
                  {p.raw}
                </text>
              </g>
            ))}
          </svg>
        )}
        <div style={S.chartLegend}>
          <span style={{ color: '#c8943e' }}>━━ sentence count (left)</span>
          <span style={{ color: '#27ae60' }}>━━ avg score (right)</span>
        </div>
      </div>
    </div>
  )
}

/* ==================== Weak Sentences ==================== */
function WeakSentences() {
  const [weak, setWeak] = useState<any[]>([])
  const [loaded, setLoaded] = useState(false)
  const [threshold, setThreshold] = useState(0.7)

  useEffect(() => {
    fetch(`/api/history/weak?threshold=${threshold}`).then(r => r.json()).then(d => { setWeak(d); setLoaded(true) })
  }, [threshold])

  return (
    <div>
      <div style={S.weakHeader}>
        <span style={S.weakTitle}>Weak Sentences</span>
        <div style={S.thresholdControl}>
          <span style={{ fontSize: '0.85rem', color: '#8b7355' }}>Threshold:</span>
          <select style={S.thresholdSelect} value={threshold} onChange={e => { setLoaded(false); setThreshold(Number(e.target.value)) }}>
            <option value={0.5}>50%</option>
            <option value={0.6}>60%</option>
            <option value={0.7}>70%</option>
            <option value={0.8}>80%</option>
          </select>
        </div>
      </div>
      {weak.length === 0 && loaded && <div style={S.empty}>No weak sentences. Great job! 🎉</div>}
      {weak.map((w, i) => (
        <div key={i} style={S.weakCard}>
          <div style={S.weakLeft}>
            <div style={S.weakText}>{w.text}</div>
            {w.text_zh && <div style={S.weakZh}>{w.text_zh}</div>}
            <div style={S.weakMeta}>
              <span style={{ ...S.hitBadge, background: '#fadbd8', color: '#c0392b' }}>{(w.avg_hit_ratio * 100).toFixed(0)}%</span>
              <span>{w.attempt_count} attempts</span>
              <span>avg: {(w.avg_hit_ratio * 100).toFixed(0)}%</span>
            </div>
          </div>
          {w.audio_path && <audio controls src={`/data/recordings/${w.audio_path}`} style={S.audioPlayer} preload="none" />}
        </div>
      ))}
    </div>
  )
}

/* ==================== Styles ==================== */
const S: Record<string, React.CSSProperties> = {
  page: { maxWidth: 800, margin: '0 auto', padding: '1.5rem 1.5rem 3rem', fontFamily: 'Nunito, PingFang SC, Microsoft YaHei, sans-serif', background: '#fdf6e8', minHeight: '100vh' },
  pageTitle: { fontSize: '1.8rem', fontWeight: 900, color: '#c8943e', marginBottom: '1rem' },
  tabBar: { display: 'flex', gap: 8, marginBottom: '1.5rem', flexWrap: 'wrap' },
  tab: { padding: '7px 16px', borderRadius: 20, border: '2px solid #e8dcc8', background: 'white', color: '#8b6914', fontSize: '0.9rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' },
  tabActive: { background: '#d4a574', color: 'white', border: '2px solid #d4a574' },
  loading: { textAlign: 'center', color: '#b89a6a', padding: '3rem' },
  empty: { textAlign: 'center', color: '#b89a6a', padding: '3rem', fontSize: '1rem' },

  listHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  listTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#5a3e1b' },
  listItem: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', marginBottom: 8, background: 'rgba(255,255,255,0.85)', borderRadius: 14, border: '2px solid #e8dcc8' },
  listItemTitle: { fontSize: '1rem', fontWeight: 700, color: '#5a3e1b' },
  listItemMeta: { fontSize: '0.8rem', color: '#b89a6a', marginTop: 2 },

  editorHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, gap: 10 },
  editorTitle: { fontSize: '1.1rem', fontWeight: 700, color: '#5a3e1b', flex: 1, textAlign: 'center' },
  status: { padding: '8px 14px', borderRadius: 12, marginBottom: 12, background: 'rgba(255,255,255,0.8)', fontWeight: 700, fontSize: '0.85rem' },
  fieldGroup: { marginBottom: 14 },
  label: { display: 'block', fontWeight: 700, color: '#5a3e1b', marginBottom: 6, fontSize: '0.9rem' },
  input: { width: '100%', padding: '10px 14px', borderRadius: 12, border: '2px solid #e8dcc8', fontSize: '1rem', fontFamily: 'inherit', background: 'rgba(255,255,255,0.8)' },

  itemsSection: { marginTop: 8 },
  itemsHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  itemsLabel: { fontWeight: 700, color: '#5a3e1b', fontSize: '0.95rem' },
  itemCard: { display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12, background: 'rgba(255,255,255,0.85)', borderRadius: 14, border: '2px solid #e8dcc8', padding: 12 },
  itemNumber: { width: 26, height: 26, borderRadius: '50%', background: '#d4a574', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8rem', flexShrink: 0, marginTop: 4 },
  itemContent: { flex: 1, display: 'flex', gap: 10, minHeight: 80 },
  imageArea: { flexShrink: 0, width: 80, height: 80 },
  imagePreview: { position: 'relative', width: 80, height: 80, borderRadius: 10, overflow: 'hidden' },
  previewImg: { width: '100%', height: '100%', objectFit: 'cover' },
  removeImgBtn: { position: 'absolute', top: 3, right: 3, width: 18, height: 18, borderRadius: '50%', border: 'none', background: 'rgba(0,0,0,0.5)', color: 'white', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  uploadLabel: { cursor: 'pointer', display: 'block' },
  uploadPlaceholder: { width: 80, height: 80, borderRadius: 10, border: '2px dashed #d4c4a8', background: '#faf4e6', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 },
  uploadIcon: { fontSize: '1.2rem', opacity: 0.5 },
  uploadText: { fontSize: '0.6rem', color: '#b89a6a' },
  textFields: { flex: 1, display: 'flex', flexDirection: 'column', gap: 5 },
  itemInput: { width: '100%', padding: '6px 10px', borderRadius: 8, border: '2px solid #e8dcc8', fontSize: '0.85rem', fontFamily: 'inherit', background: 'rgba(255,255,255,0.8)' },
  ttsRow: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 },
  ttsPlayBtn: { width: 26, height: 26, borderRadius: '50%', border: '1px solid #d4a574', background: '#fff8ee', color: '#c8943e', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  ttsRegenBtn: { width: 26, height: 26, borderRadius: '50%', border: '1px solid #d4c4a8', background: 'white', fontSize: '0.7rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyItems: { textAlign: 'center', color: '#b89a6a', padding: '2rem', background: 'rgba(255,255,255,0.5)', borderRadius: 14, border: '2px dashed #e8dcc8' },

  primaryBtn: { padding: '7px 16px', borderRadius: 20, border: 'none', background: '#d4a574', color: 'white', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' },
  secondaryBtn: { padding: '7px 14px', borderRadius: 20, border: '2px solid #d4a574', background: 'white', color: '#8b6914', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' },
  editBtn: { padding: '5px 14px', borderRadius: 12, border: '2px solid #d4a574', background: 'white', color: '#8b6914', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' },
  addBtn: { padding: '5px 14px', borderRadius: 12, border: '2px solid #27ae60', background: 'white', color: '#27ae60', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' },
  removeBtn: { width: 28, height: 28, borderRadius: '50%', border: '2px solid #e0d5c0', background: 'white', color: '#c0392b', fontSize: '1.1rem', fontWeight: 700, cursor: 'pointer', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 4 },
  ttsBtn: { padding: '7px 12px', borderRadius: 20, border: '2px solid #3498db', background: 'white', color: '#2980b9', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap' },

  /* Chart */
  chartSection: { background: 'rgba(255,255,255,0.85)', borderRadius: 16, border: '2px solid #e8dcc8', padding: '16px 20px', marginBottom: 20 },
  chartHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  chartTitle: { fontSize: '1rem', fontWeight: 700, color: '#5a3e1b' },
  dateSelect: { display: 'flex', alignItems: 'center', gap: 8 },
  dateInput: {
    padding: '4px 8px', borderRadius: 8, border: '1px solid #e8dcc8',
    fontSize: '0.8rem', fontFamily: 'inherit', background: 'white', color: '#5a3e1b',
  },
  chartLegend: { display: 'flex', gap: 16, marginTop: 10, fontSize: '0.75rem', color: '#8b7355' },

  /* Weak */
  weakHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  weakTitle: { fontSize: '1rem', fontWeight: 700, color: '#5a3e1b' },
  thresholdControl: { display: 'flex', alignItems: 'center', gap: 8 },
  thresholdSelect: { padding: '4px 8px', borderRadius: 8, border: '2px solid #e8dcc8', fontSize: '0.85rem', fontFamily: 'inherit', background: 'white' },
  weakCard: { display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', marginBottom: 10, background: 'rgba(255,255,255,0.85)', borderRadius: 14, border: '2px solid #e8dcc8' },
  weakLeft: { flex: 1, minWidth: 0 },
  weakText: { fontSize: '0.95rem', fontWeight: 700, color: '#5a3e1b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  weakZh: { fontSize: '0.8rem', color: '#8b7355', marginTop: 2 },
  weakMeta: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, fontSize: '0.75rem', color: '#b89a6a' },
  hitBadge: { padding: '1px 8px', borderRadius: 10, fontWeight: 700, fontSize: '0.75rem' },
  audioPlayer: { width: 160, height: 32, flexShrink: 0 },

  /* Settings */
  settingRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '14px 16px', marginBottom: 10, background: 'rgba(255,255,255,0.85)',
    borderRadius: 14, border: '2px solid #e8dcc8',
  },
  settingLabel: { fontSize: '0.95rem', fontWeight: 700, color: '#5a3e1b' },
  settingHint: { fontSize: '0.8rem', color: '#b89a6a', marginTop: 2 },
}
