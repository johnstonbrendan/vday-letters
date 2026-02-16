import { useEffect, useState } from 'react'
import { Heart, Mail, MailCheck } from 'lucide-react'
import { checkExists, getRoomStatuses, type RoomStatus } from '../lib/supabase'

export type Room = {
  id: string
  name: string
  color: string
  gridArea: string
}

export const ROOMS: Room[] = [
  { id: 'bedroom', name: 'Bedroom', color: 'bg-lavender', gridArea: '1 / 1 / 3 / 2' },
  { id: 'study', name: 'Office', color: 'bg-sky', gridArea: '1 / 2 / 2 / 3' },
  { id: 'bathroom', name: 'Bathroom', color: 'bg-mint', gridArea: '2 / 2 / 3 / 3' },
  { id: 'living-room', name: 'Living Room', color: 'bg-peach', gridArea: '1 / 3 / 3 / 4' },
]

export function FloorPlan({
  onRoomClick,
  refreshKey,
}: {
  onRoomClick: (room: Room) => void
  refreshKey: number
}) {
  const [recorded, setRecorded] = useState<Record<string, boolean>>({})
  const [statuses, setStatuses] = useState<Record<string, RoomStatus>>({})

  useEffect(() => {
    ROOMS.forEach((room) => {
      checkExists(room.id).then((exists) => {
        setRecorded((prev) => ({ ...prev, [room.id]: exists }))
      })
    })
    getRoomStatuses().then(setStatuses)
  }, [refreshKey])

  return (
    <div className="min-h-screen bg-cream flex flex-col items-center justify-center p-4">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-rose-dark flex items-center justify-center gap-2">
          <Heart className="w-7 h-7 fill-rose text-rose" />
          Voice Letters
          <Heart className="w-7 h-7 fill-rose text-rose" />
        </h1>
        <p className="text-rose-dark/60 mt-2 text-sm">Tap a room to send a voice letter</p>
      </div>

      <div
        className="grid gap-2 w-full max-w-lg aspect-[3/2]"
        style={{
          gridTemplateRows: '1fr 1fr',
          gridTemplateColumns: '1.2fr 0.8fr 1.2fr',
        }}
      >
        {ROOMS.map((room) => (
          <button
            key={room.id}
            onClick={() => onRoomClick(room)}
            className={`${room.color} rounded-2xl border-2 border-white/60
                       flex flex-col items-center justify-center gap-2 relative
                       hover:scale-[1.02] active:scale-[0.98] transition-transform
                       cursor-pointer shadow-sm hover:shadow-md`}
            style={{ gridArea: room.gridArea }}
          >
            {recorded[room.id] ? (
              statuses[room.id]?.played_at ? (
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <MailCheck className="w-4 h-4 text-green-600" />
                </div>
              ) : (
                <div className="w-8 h-8 bg-rose/20 rounded-full flex items-center justify-center">
                  <Mail className="w-4 h-4 text-rose-deep" />
                </div>
              )
            ) : (
              <Heart className="w-5 h-5 text-rose-dark/40 fill-rose-dark/20" />
            )}
            <span className="font-semibold text-rose-dark/80 text-sm sm:text-base">
              {room.name}
            </span>
            {recorded[room.id] && (
              <span className="text-[11px] font-medium" style={{
                color: statuses[room.id]?.played_at ? 'rgb(22 163 74 / 0.7)' : 'rgb(159 18 57 / 0.6)'
              }}>
                {statuses[room.id]?.played_at ? 'Delivered' : 'In mailbox'}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
