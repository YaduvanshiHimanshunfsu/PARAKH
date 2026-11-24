import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { getToken, officerApi, onAuthExpired, setToken } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(() => Boolean(getToken()))

  // A stored token may have expired server-side, so validate it once.
  useEffect(() => {
    if (!getToken()) return undefined
    let cancelled = false
    officerApi
      .me()
      .then((me) => !cancelled && setUser(me))
      .catch(() => {
        if (!cancelled) {
          setToken(null)
          setUser(null)
        }
      })
      .finally(() => !cancelled && setChecking(false))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => onAuthExpired(() => setUser(null)), [])

  const signIn = useCallback(async (username, password) => {
    const session = await officerApi.login(username, password)
    setToken(session.token)
    const me = { username: session.username, role: session.role, expires_at: session.expires_at }
    setUser(me)
    return me
  }, [])

  const signOut = useCallback(async () => {
    try {
      await officerApi.logout()
    } catch {
      /* best effort: the local session is cleared regardless */
    }
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, checking, signIn, signOut, isOfficer: Boolean(user) }), [user, checking, signIn, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}

export function RequireOfficer({ children }) {
  const { isOfficer, checking } = useAuth()
  const location = useLocation()
  if (checking) {
    return <div className="grid min-h-[50vh] place-items-center text-body-sm text-ink-2">Checking your session…</div>
  }
  if (!isOfficer) return <Navigate to="/investigate/login" replace state={{ from: location.pathname }} />
  return children
}
