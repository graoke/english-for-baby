/**
 * Shared recording utilities — MIME detection, MediaRecorder lifecycle, upload.
 */

export function isWebMSupported(): boolean {
  if (typeof MediaRecorder === 'undefined') return false
  return MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
}

export function isMP4Supported(): boolean {
  if (typeof MediaRecorder === 'undefined') return false
  return MediaRecorder.isTypeSupported('audio/mp4')
}

export function getSupportedMimeType(): string {
  if (isWebMSupported()) return 'audio/webm;codecs=opus'
  if (isMP4Supported()) return 'audio/mp4'
  return ''
}

export interface RecordingResult {
  blob: Blob
  durationMs: number
  filename: string
}

export interface StartRecordingOptions {
  onRecordingComplete: (result: RecordingResult) => void
  onError?: (error: string) => void
}

/**
 * Start a recording using the MediaRecorder API.
 * Returns a stop function and the recorder instance.
 */
export async function startRecording(
  opts: StartRecordingOptions,
): Promise<{ stop: () => void; recorder: MediaRecorder } | null> {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    opts.onError?.('浏览器不支持录音（需要 HTTPS 或 localhost）')
    return null
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mimeType = getSupportedMimeType()
  const recorderOptions: MediaRecorderOptions = {}
  if (mimeType) recorderOptions.mimeType = mimeType

  const recorder = new MediaRecorder(stream, recorderOptions)
  const chunks: Blob[] = []
  const startTime = Date.now()

  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data)
  }

  recorder.onstop = () => {
    stream.getTracks().forEach((t) => t.stop())
    const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
    const ext = recorder.mimeType?.includes('mp4') ? 'mp4' : 'webm'
    opts.onRecordingComplete({
      blob,
      durationMs: Date.now() - startTime,
      filename: `recording.${ext}`,
    })
  }

  recorder.onerror = () => {
    stream.getTracks().forEach((t) => t.stop())
    opts.onError?.('录音出错，请重试')
  }

  recorder.start()
  return {
    stop: () => recorder.stop(),
    recorder,
  }
}

/**
 * Upload a recording to the server (fire-and-forget).
 */
export function uploadRecording(blob: Blob, itemId: number, durationMs: number): void {
  const fd = new FormData()
  fd.append('file', blob, 'recording.webm')
  fetch(`/api/attempts?drill_item_id=${itemId}&duration_ms=${durationMs}`, {
    method: 'POST',
    body: fd,
  }).catch((e) => console.error('Upload failed:', e))
}
