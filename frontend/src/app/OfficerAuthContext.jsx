import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import * as api from '../lib/investigateApi'

const OfficerAuthContext = createContext(null)

export function OfficerAuthProvider({ children }) {
  const [user, setUser] = useState(() => api.getStoredUser())
  const [checking, setChecking] = useState(Boolean(api.getToken()))

  // A stored token may have expired server-side while the tab was closed, so
  // it is validated once on mount rather than trusted.
  useEffect(() => {
    let cancelled = false
    if (!api.getToken()) {
      setChecking(false)
      return undefined
    }
    api
      .whoAmI()
      .then((me) => {
        if (!cancelled) setUser({ username: me.username, role: me.role })
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (username, password) => {
    const signedIn = await api.login(username, password)
    setUser(signedIn)
    return signedIn
  }, [])

  const signOut = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, checking, signIn, signOut, isAuthenticated: Boolean(user) }),
    [user, checking, signIn, signOut],
  )

  return <OfficerAuthContext.Provider value={value}>{children}</OfficerAuthContext.Provider>
}

export function useOfficerAuth() {
  const context = useContext(OfficerAuthContext)
  if (!context) throw new Error('useOfficerAuth must be used inside OfficerAuthProvider')
  return context
}

export function RequireOfficer({ children }) {
  const { isAuthenticated, checking } = useOfficerAuth()
  const location = useLocation()

  if (checking) {
    return (
      <div className="grid min-h-[50vh] place-items-center text-sm text-slate-500">
        Checking your session…
      </div>
    )
  }
  if (!isAuthenticated) {
    return <Navigate to="/investigate/login" replace state={{ from: location.pathname }} />
  }
  return children
}
