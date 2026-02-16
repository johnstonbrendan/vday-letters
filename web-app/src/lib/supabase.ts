import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

const isConfigured = Boolean(supabaseUrl && supabaseAnonKey)

export const supabase: SupabaseClient | null = isConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null

if (!isConfigured) {
  console.warn(
    '[Voice Letters] Supabase not configured — uploads/downloads disabled. ' +
    'Create a .env file with VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.'
  )
}

export const BUCKET = 'voice-messages'

export async function getPlaybackUrl(roomName: string): Promise<string> {
  if (!supabase) return ''
  const { data, error } = await supabase.storage
    .from(BUCKET)
    .createSignedUrl(`${roomName}.webm`, 300) // 5 min expiry
  if (error || !data?.signedUrl) return ''
  return data.signedUrl
}

async function archiveExisting(roomName: string): Promise<void> {
  if (!supabase) return
  const exists = await checkExists(roomName)
  if (!exists) return

  const ts = new Date().toISOString().replace(/[:.]/g, '-')
  await supabase.storage
    .from(BUCKET)
    .move(`${roomName}.webm`, `archive/${roomName}_${ts}.webm`)
}

export async function uploadAudio(roomName: string, blob: Blob): Promise<void> {
  if (!supabase) {
    console.warn('[Voice Letters] Upload skipped — Supabase not configured')
    return
  }
  await archiveExisting(roomName)
  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(`${roomName}.webm`, blob, {
      contentType: 'audio/webm',
    })
  if (error) throw error

  // Mark as pending (new recording, not yet played)
  await supabase.from('room_status').upsert({
    room_name: roomName,
    updated_at: new Date().toISOString(),
    played_at: null,
  })
}

export async function checkExists(roomName: string): Promise<boolean> {
  if (!supabase) return false
  const { data, error } = await supabase.storage
    .from(BUCKET)
    .list('', { search: `${roomName}.webm` })
  if (error) return false
  return data.some((f) => f.name === `${roomName}.webm`)
}

export async function deleteAudio(roomName: string): Promise<void> {
  if (!supabase) return
  await archiveExisting(roomName)

  // Clear the status row
  await supabase.from('room_status').upsert({
    room_name: roomName,
    updated_at: new Date().toISOString(),
    played_at: new Date().toISOString(), // not pending
  })
}

export type RoomStatus = {
  room_name: string
  updated_at: string
  played_at: string | null
}

export async function replayAudio(roomName: string): Promise<void> {
  if (!supabase) return
  await supabase.from('room_status').upsert({
    room_name: roomName,
    updated_at: new Date().toISOString(),
    played_at: null,
  })
}

export async function getRoomStatuses(): Promise<Record<string, RoomStatus>> {
  if (!supabase) return {}
  const { data, error } = await supabase
    .from('room_status')
    .select('*')
  if (error || !data) return {}
  const map: Record<string, RoomStatus> = {}
  for (const row of data) {
    map[row.room_name] = row
  }
  return map
}
