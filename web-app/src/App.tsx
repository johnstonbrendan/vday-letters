import { useState } from 'react'
import { FloorPlan, type Room } from './components/FloorPlan'
import { RoomModal } from './components/RoomModal'

function App() {
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <>
      <FloorPlan onRoomClick={setSelectedRoom} refreshKey={refreshKey} />
      {selectedRoom && (
        <RoomModal
          room={selectedRoom}
          onClose={() => setSelectedRoom(null)}
          onSaved={() => setRefreshKey((k) => k + 1)}
        />
      )}
    </>
  )
}

export default App
