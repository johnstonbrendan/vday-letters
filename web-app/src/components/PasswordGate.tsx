import { useState } from 'react'
import { Heart } from 'lucide-react'

const STORAGE_KEY = 'vday-letters-auth'

export function useAuth() {
  const [authed, setAuthed] = useState(
    () => localStorage.getItem(STORAGE_KEY) === 'true'
  )

  function login(password: string): boolean {
    const expected = import.meta.env.VITE_PASSWORD || 'valentine'
    if (password === expected) {
      localStorage.setItem(STORAGE_KEY, 'true')
      setAuthed(true)
      return true
    }
    return false
  }

  return { authed, login }
}

export function PasswordGate({ onLogin }: { onLogin: (pw: string) => boolean }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [shake, setShake] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!onLogin(password)) {
      setError(true)
      setShake(true)
      setTimeout(() => setShake(false), 500)
    }
  }

  return (
    <div className="fixed inset-0 bg-cream flex items-center justify-center z-50">
      <form
        onSubmit={handleSubmit}
        className={`flex flex-col items-center gap-6 p-10 ${shake ? 'animate-shake' : ''}`}
      >
        <Heart className="w-16 h-16 text-rose fill-rose" />
        <h1 className="text-2xl font-semibold text-rose-dark">Voice Letters</h1>
        <p className="text-rose-dark/70 text-sm">Enter the password to continue</p>
        <input
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value)
            setError(false)
          }}
          placeholder="Password"
          autoFocus
          className="w-64 px-4 py-3 rounded-xl border-2 border-blush bg-white text-center text-lg
                     focus:outline-none focus:border-rose transition-colors placeholder:text-rose/30"
        />
        {error && (
          <p className="text-rose-deep text-sm">Wrong password, try again</p>
        )}
        <button
          type="submit"
          className="px-8 py-3 bg-rose text-white rounded-xl font-medium
                     hover:bg-rose-dark transition-colors cursor-pointer"
        >
          Enter
        </button>
      </form>

      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-8px); }
          40%, 80% { transform: translateX(8px); }
        }
        .animate-shake { animation: shake 0.4s ease-in-out; }
      `}</style>
    </div>
  )
}
