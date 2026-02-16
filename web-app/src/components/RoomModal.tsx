import { useState, useEffect, useRef } from 'react'
import { X, Mic, Square, Play, Pause, Send, RotateCcw, MailCheck, Loader2, Trash2, RefreshCw } from 'lucide-react'
import { type Room } from './FloorPlan'
import { useRecorder } from '../hooks/useRecorder'
import { uploadAudio, checkExists, getPlaybackUrl, deleteAudio, replayAudio, getRoomStatuses, type RoomStatus } from '../lib/supabase'

type Props = {
  room: Room
  onClose: () => void
  onSaved: () => void
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function RoomModal({ room, onClose, onSaved }: Props) {
  const { state, blob, duration, start, stop, reset } = useRecorder()
  const [hasExisting, setHasExisting] = useState<boolean | null>(null)
  const [playing, setPlaying] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [deleted, setDeleted] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [playingExisting, setPlayingExisting] = useState(false)
  const [replaying, setReplaying] = useState(false)
  const [roomStatus, setRoomStatus] = useState<RoomStatus | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const existingAudioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    checkExists(room.id).then(setHasExisting)
    getRoomStatuses().then((statuses) => {
      setRoomStatus(statuses[room.id] ?? null)
    })
  }, [room.id])

  function togglePreview() {
    if (!blob) return
    if (playing) {
      audioRef.current?.pause()
      setPlaying(false)
    } else {
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => setPlaying(false)
      audio.play()
      audioRef.current = audio
      setPlaying(true)
    }
  }

  async function toggleExisting() {
    if (playingExisting) {
      existingAudioRef.current?.pause()
      setPlayingExisting(false)
    } else {
      const url = await getPlaybackUrl(room.id)
      if (!url) return
      const audio = new Audio(url)
      audio.onended = () => setPlayingExisting(false)
      audio.play()
      existingAudioRef.current = audio
      setPlayingExisting(true)
    }
  }

  async function handleSave() {
    if (!blob) return
    setSaving(true)
    try {
      await uploadAudio(room.id, blob)
      setSaved(true)
      onSaved()
      setTimeout(() => {
        onClose()
      }, 1200)
    } catch (err) {
      console.error('Upload failed:', err)
      alert('Upload failed. Check your Supabase configuration.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      existingAudioRef.current?.pause()
      setPlayingExisting(false)
      await deleteAudio(room.id)
      setDeleted(true)
      onSaved()
      setTimeout(() => {
        onClose()
      }, 1200)
    } catch (err) {
      console.error('Delete failed:', err)
      alert('Delete failed.')
    } finally {
      setDeleting(false)
    }
  }

  async function handleReplay() {
    setReplaying(true)
    try {
      await replayAudio(room.id)
      onSaved()
      setRoomStatus((prev) => prev ? { ...prev, played_at: null } : null)
    } catch (err) {
      console.error('Replay failed:', err)
    } finally {
      setReplaying(false)
    }
  }

  function handleClose() {
    audioRef.current?.pause()
    existingAudioRef.current?.pause()
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={handleClose}>
      <div
        className="bg-white rounded-3xl p-6 w-full max-w-sm shadow-xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-rose-dark/40 hover:text-rose-dark cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-xl font-semibold text-rose-dark text-center mb-1">
          {room.name}
        </h2>

        {hasExisting && state === 'idle' && !saved && (
          <p className="text-xs text-rose-dark/40 text-center mb-5">
            Sending a new letter will replace the current one
          </p>
        )}

        {!hasExisting && state === 'idle' && !saved && (
          <div className="mb-5" />
        )}

        {/* Existing recording */}
        {hasExisting && state === 'idle' && !saved && !deleted && (
          <div className="mb-6 p-4 bg-blush/50 rounded-2xl">
            <p className="text-sm text-rose-dark/60 text-center mb-3">Current letter</p>
            <div className="flex gap-2">
              <button
                onClick={toggleExisting}
                className="flex-1 flex items-center justify-center gap-2 py-2 px-4
                           bg-white rounded-xl text-rose-dark font-medium
                           hover:bg-rose/10 transition-colors cursor-pointer"
              >
                {playingExisting ? (
                  <><Pause className="w-4 h-4" /> Pause</>
                ) : (
                  <><Play className="w-4 h-4" /> Listen</>
                )}
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center justify-center gap-2 py-2 px-4
                           bg-white rounded-xl text-red-400 font-medium
                           hover:bg-red-50 transition-colors cursor-pointer
                           disabled:opacity-50"
              >
                {deleting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
              </button>
            </div>
            {(!roomStatus || roomStatus.played_at) && (
              <button
                onClick={handleReplay}
                disabled={replaying}
                className="w-full mt-2 flex items-center justify-center gap-2 py-2
                           bg-white rounded-xl text-rose-dark font-medium
                           hover:bg-rose/10 transition-colors cursor-pointer
                           disabled:opacity-50"
              >
                {replaying ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Resending...</>
                ) : (
                  <><RefreshCw className="w-4 h-4" /> Resend letter</>
                )}
              </button>
            )}
            {roomStatus && !roomStatus.played_at && (
              <p className="text-xs text-rose-dark/50 text-center mt-2">
                Waiting for pickup
              </p>
            )}
          </div>
        )}

        {/* Saved confirmation */}
        {saved && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="w-16 h-16 bg-mint rounded-full flex items-center justify-center">
              <MailCheck className="w-8 h-8 text-green-700" />
            </div>
            <p className="text-rose-dark font-medium">Letter sent!</p>
          </div>
        )}

        {/* Deleted confirmation */}
        {deleted && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
              <Trash2 className="w-8 h-8 text-red-400" />
            </div>
            <p className="text-rose-dark font-medium">Letter removed</p>
          </div>
        )}

        {/* Idle: show record button */}
        {state === 'idle' && !saved && !deleted && (
          <div className="flex flex-col items-center gap-4">
            <button
              onClick={start}
              className="w-20 h-20 bg-rose rounded-full flex items-center justify-center
                         hover:bg-rose-dark transition-colors shadow-lg
                         hover:shadow-xl active:scale-95 cursor-pointer"
            >
              <Mic className="w-8 h-8 text-white" />
            </button>
            <p className="text-sm text-rose-dark/50">
              {hasExisting ? 'Tap to write a new letter' : 'Tap to write a letter'}
            </p>
          </div>
        )}

        {/* Recording */}
        {state === 'recording' && (
          <div className="flex flex-col items-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-rose/30 rounded-full animate-ping" />
              <button
                onClick={stop}
                className="relative w-20 h-20 bg-rose-deep rounded-full flex items-center justify-center
                           shadow-lg cursor-pointer"
              >
                <Square className="w-6 h-6 text-white fill-white" />
              </button>
            </div>
            <p className="text-rose-dark font-mono text-lg">{formatTime(duration)}</p>
            <p className="text-sm text-rose-dark/50">Tap to stop</p>
          </div>
        )}

        {/* Recorded: preview + save */}
        {state === 'recorded' && !saved && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-sm text-rose-dark/60">{formatTime(duration)} recorded</p>
            <div className="flex gap-3">
              <button
                onClick={togglePreview}
                className="flex items-center gap-2 px-5 py-2.5 bg-blush rounded-xl
                           text-rose-dark font-medium hover:bg-blush/80 transition-colors cursor-pointer"
              >
                {playing ? (
                  <><Pause className="w-4 h-4" /> Pause</>
                ) : (
                  <><Play className="w-4 h-4" /> Preview</>
                )}
              </button>
              <button
                onClick={reset}
                className="flex items-center gap-2 px-5 py-2.5 bg-blush rounded-xl
                           text-rose-dark font-medium hover:bg-blush/80 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-4 h-4" /> Redo
              </button>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 py-3 bg-rose text-white
                         rounded-xl font-medium hover:bg-rose-dark transition-colors
                         disabled:opacity-50 cursor-pointer"
            >
              {saving ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Sending...</>
              ) : hasExisting ? (
                <><Send className="w-4 h-4" /> Send letter</>
              ) : (
                <><Send className="w-4 h-4" /> Send letter</>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
