import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Brand } from '../../app/Brand'
import { useAuth } from '../../app/AuthContext'
import { Button, Icon } from '../../design/ui'

// Built from design/stitch/parakh_officer_login_law_enforcement_authentication.
// Removed per H.1: SSO / RajKaj / biometric / OTP options (not implemented)
// and "ISO certified" badges. The form talks to POST /investigate/auth/login.

const FEATURES = [
  ['hub', 'Link cases that share a UPI ID, number, domain or app signer'],
  ['local_fire_department', 'See which identifiers are rising this week'],
  ['android', 'Read APK permissions, certificates and hidden endpoints'],
  ['description', 'Export a case report or CSV for the investigation file'],
]

export function LoginPage() {
  const { signIn, isOfficer } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const destination = typeof location.state?.from === 'string' && location.state.from.startsWith('/investigate') ? location.state.from : '/investigate'

  if (isOfficer) return <Navigate to={destination} replace />

  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await signIn(username.trim(), password)
      navigate(destination, { replace: true })
    } catch (caught) {
      setError(
        caught.status === 401
          ? 'Wrong username or password.'
          : caught.status === 429
            ? 'Too many attempts. Wait a minute and try again.'
            : caught.status === 422
              ? 'Username must be at least 3 characters and password at least 8.'
              : caught.message,
      )
    } finally {
      setBusy(false)
    }
  }

  const field = 'h-12 w-full rounded-chip border-[1.5px] border-line bg-white px-3 text-body-md outline-none focus:border-primary'

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-gradient-to-br from-[#1e3a8a] via-primary to-[#1e40af] p-12 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-10 h-80 w-80 rounded-full bg-accent/20 blur-3xl" />
        <p className="text-label-ui uppercase text-white/70">Rajasthan Police · Investigation mode</p>
        <h1 className="mt-3 max-w-lg text-[40px] font-extrabold leading-[48px] tracking-tight">Turn scattered complaints into connected cases.</h1>
        <ul className="mt-10 space-y-4">
          {FEATURES.map(([icon, text]) => (
            <li key={text} className="flex items-center gap-3 text-body-lg text-white/90">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/15"><Icon name={icon} /></span>
              {text}
            </li>
          ))}
        </ul>
        <p className="mt-auto max-w-lg text-body-sm text-white/70">
          Indicators from automated analysis support an investigation; they are not proof of criminal conduct. Every sign-in is logged.
        </p>
      </section>

      <section className="flex flex-col items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <Brand subtitle="Investigation console" />
          <h2 className="mt-8 text-headline-md">Officer sign-in</h2>
          <p className="hi text-body-md text-ink-2" lang="hi">अधिकारी लॉगिन</p>
          <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
            <label className="block text-body-sm font-semibold text-ink">
              Username
              <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className={`${field} mt-1`} required minLength={3} />
            </label>
            <div>
              <label htmlFor="officer-password" className="block text-body-sm font-semibold text-ink">Password</label>
              <div className="relative mt-1">
                <input
                  id="officer-password"
                  type={show ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className={`${field} pr-12`}
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShow(!show)}
                  aria-label={show ? 'Hide password' : 'Show password'}
                  aria-controls="officer-password"
                  className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-lg text-ink-2 hover:bg-canvas"
                >
                  <Icon name={show ? 'visibility_off' : 'visibility'} size={20} />
                </button>
              </div>
            </div>
            {error && (
              <p role="alert" className="flex items-start gap-2 rounded-chip bg-risk-high-bg p-3 text-body-sm text-risk-high-ink">
                <Icon name="error" size={18} filled /> {error}
              </p>
            )}
            <Button type="submit" block size="lg" icon="login" loading={busy} disabled={!username.trim() || !password}>
              Sign in
            </Button>
          </form>
          <p className="mt-6 text-body-sm text-ink-3">
            Accounts are issued by the PARAKH administrator for this deployment. Your session is kept only in this browser tab and expires on the server.
          </p>
          <a href="/" className="mt-4 inline-flex items-center gap-1 text-body-sm font-semibold text-primary hover:underline">
            <Icon name="arrow_back" size={16} /> Citizen portal
          </a>
        </div>
      </section>
    </div>
  )
}

export default LoginPage
