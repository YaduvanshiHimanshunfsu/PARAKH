import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useOfficerAuth } from '../../app/OfficerAuthContext'
import { ErrorNote } from '../../features/investigate/ui'

export function LoginPage() {
  const { signIn, isAuthenticated, checking } = useOfficerAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (checking) {
    return <div className="grid min-h-screen place-items-center text-sm text-slate-500">Checking your session…</div>
  }
  if (isAuthenticated) {
    return <Navigate to={location.state?.from || '/investigate'} replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await signIn(username.trim(), password)
      navigate(location.state?.from || '/investigate', { replace: true })
    } catch (caught) {
      setError(caught.message || 'Sign-in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center text-white">
          <span className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-xl bg-blue-600">
            <ShieldAlert size={24} />
          </span>
          <h1 className="text-lg font-bold">PARAKH Investigate</h1>
          <p className="text-sm text-slate-400">Authorised officers only</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl bg-white p-6 shadow-xl"
          aria-label="Officer sign in"
        >
          <ErrorNote message={error} />

          <div>
            <label htmlFor="username" className="mb-1 block text-xs font-bold text-slate-700">
              Username
            </label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-xs font-bold text-slate-700">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </div>

          <button
            type="submit"
            disabled={busy || !username.trim() || !password}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="text-center text-[11px] text-slate-500">
            Access is logged. Case data is for authorised investigation only.
          </p>
        </form>
      </div>
    </div>
  )
}
