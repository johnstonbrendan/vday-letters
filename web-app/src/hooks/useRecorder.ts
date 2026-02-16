import { useState, useRef, useCallback } from 'react'

export type RecorderState = 'idle' | 'recording' | 'recorded'

export function useRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [blob, setBlob] = useState<Blob | null>(null)
  const [duration, setDuration] = useState(0)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const startTime = useRef(0)
  const timerRef = useRef<number>(0)

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    chunks.current = []

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.current.push(e.data)
    }

    recorder.onstop = () => {
      const recorded = new Blob(chunks.current, { type: 'audio/webm' })
      setBlob(recorded)
      setState('recorded')
      clearInterval(timerRef.current)
      stream.getTracks().forEach((t) => t.stop())
    }

    mediaRecorder.current = recorder
    recorder.start()
    startTime.current = Date.now()
    setDuration(0)
    setState('recording')

    timerRef.current = window.setInterval(() => {
      setDuration(Math.floor((Date.now() - startTime.current) / 1000))
    }, 200)
  }, [])

  const stop = useCallback(() => {
    mediaRecorder.current?.stop()
  }, [])

  const reset = useCallback(() => {
    setBlob(null)
    setState('idle')
    setDuration(0)
  }, [])

  return { state, blob, duration, start, stop, reset }
}
