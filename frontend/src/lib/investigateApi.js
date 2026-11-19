// Officer-authenticated API client for Investigation Mode.
//
// The token lives in sessionStorage, not localStorage: an officer console
// should not survive the tab being closed on a shared machine.

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const TOKEN_KEY = 'parakh.officer.token'
const USER_KEY = 'parakh.officer.user'

export class AuthError extends Error {}

export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function getStoredUser() {
  try {
    const raw = sessionStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function storeSession(token, user) {
  try {
    sessionStorage.setItem(TOKEN_KEY, token)
    sessionStorage.setItem(USER_KEY, JSON.stringify(user))
  } catch {
    /* Private browsing can block storage; the session simply won't persist. */
  }
}

export function clearSession() {
  try {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
  } catch {
    /* ignore */
  }
}

async function call(path, { method = 'GET', body, isForm = false } = {}) {
  const token = getToken()
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (response.status === 401) {
    clearSession()
    throw new AuthError('Your session has expired. Please sign in again.')
  }
  if (response.status === 204) return null

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail || `Request failed (${response.status}).`)
  }
  return payload
}

function query(params) {
  const search = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value)
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

// --- auth -----------------------------------------------------------------

export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/investigate/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || 'Sign-in failed.')
  const user = { username: payload.username, role: payload.role, expiresAt: payload.expires_at }
  storeSession(payload.token, user)
  return user
}

export async function logout() {
  try {
    await call('/investigate/auth/logout', { method: 'POST' })
  } catch {
    /* Revoking server-side is best-effort; the local session is cleared regardless. */
  }
  clearSession()
}

export const whoAmI = () => call('/investigate/me')

// --- cases ----------------------------------------------------------------

export const searchCases = (filters) => call(`/investigate/cases${query(filters)}`)
export const getCase = (caseId) => call(`/investigate/cases/${encodeURIComponent(caseId)}`)
export const updateCase = (caseId, patch) =>
  call(`/investigate/cases/${encodeURIComponent(caseId)}`, { method: 'PATCH', body: patch })

export const submitArtifact = (payload) =>
  call('/investigate/submit', { method: 'POST', body: payload })

export const analyseWebsite = (payload) =>
  call('/investigate/website/analyze', { method: 'POST', body: payload })

export function uploadApk(file, reporterNote) {
  const form = new FormData()
  form.append('apk', file)
  if (reporterNote) form.append('reporter_note', reporterNote)
  return call('/investigate/apk/analyze', { method: 'POST', body: form, isForm: true })
}

// --- intelligence ---------------------------------------------------------

export const getLinkedCases = (caseId) =>
  call(`/investigate/cases/${encodeURIComponent(caseId)}/linked`)
export const getSimilarCases = (caseId) =>
  call(`/investigate/cases/${encodeURIComponent(caseId)}/similar`)
export const getIdentifierCases = (type, value) =>
  call(`/investigate/identifiers/${encodeURIComponent(type)}/cases${query({ value })}`)
export const getHeatList = (filters) => call(`/investigate/heatlist${query(filters)}`)

// --- exports --------------------------------------------------------------
// Reports open in a new tab, so the bearer token cannot ride along in a header.
// The blob is fetched here and handed to the browser as an object URL instead.

async function downloadBlob(path, filename, { open = false } = {}) {
  const token = getToken()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (response.status === 401) {
    clearSession()
    throw new AuthError('Your session has expired. Please sign in again.')
  }
  if (!response.ok) throw new Error(`Export failed (${response.status}).`)

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  if (open) {
    window.open(url, '_blank', 'noopener')
  } else {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

export const openCaseReport = (caseId, redacted) =>
  downloadBlob(
    `/investigate/cases/${encodeURIComponent(caseId)}/report${query({ redacted: redacted ? 'true' : '' })}`,
    `${caseId}.html`,
    { open: true },
  )

export const downloadCaseJson = (caseId, redacted) =>
  downloadBlob(
    `/investigate/cases/${encodeURIComponent(caseId)}/report.json${query({ redacted: redacted ? 'true' : '' })}`,
    `${caseId}.json`,
  )

export const downloadCasesCsv = (filters) =>
  downloadBlob(`/investigate/export/cases.csv${query(filters)}`, 'parakh-cases.csv')

export const downloadIdentifiersCsv = (filters) =>
  downloadBlob(`/investigate/export/identifiers.csv${query(filters)}`, 'parakh-identifiers.csv')

