// Single API client for the citizen app and the officer console.
//
// Rules (planversionalpha.md H.0):
// * one base path, same-origin by default (`/api/v1`), proxied by Vite in dev
//   and served by FastAPI in production — no CORS, no Authorization preflight;
// * route paths are lowercase. The old client called `/PARAKH/media/extract`
//   and got a 404 (defect D7); `assertRoute` makes that impossible;
// * every failure becomes an ApiError with the server's `detail` message.

const BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const TOKEN_KEY = 'parakh.officer.token'

export class ApiError extends Error {
  constructor(status, message, body = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }

  get isAuth() {
    return this.status === 401
  }

  get isRateLimited() {
    return this.status === 429
  }

  get isUnavailable() {
    return this.status === 0 || this.status === 503
  }
}

export function assertRoute(path) {
  const pathname = path.split('?')[0]
  if (!pathname.startsWith('/')) throw new Error(`API path must start with "/": ${path}`)
  if (/[A-Z]/.test(pathname)) throw new Error(`API paths are lowercase (D7): ${path}`)
  return path
}

/**
 * Build a route with dynamic segments. The fixed route text must be lowercase
 * (D7); values such as case IDs ("PRK-…") or identifier types ("UPI") are
 * URL-encoded and may use any case.
 *   route`/investigate/cases/${caseId}/linked`
 */
export function route(strings, ...values) {
  strings.forEach((part) => {
    if (/[A-Z]/.test(part.split('?')[0])) throw new Error(`API paths are lowercase (D7): ${part}`)
  })
  return strings.reduce((out, part, index) => out + part + (index < values.length ? encodeURIComponent(values[index]) : ''), '')
}

const ROUTE_CHECKED = Symbol('route-checked')
function checked(path) {
  // A path built by route() has already had its static parts validated.
  return Object.assign(new String(path), { [ROUTE_CHECKED]: true })
}

// --- officer session (sessionStorage: a console should not outlive the tab) --

export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    /* private browsing can block storage; the session simply won't persist */
  }
}

const authListeners = new Set()
export function onAuthExpired(listener) {
  authListeners.add(listener)
  return () => authListeners.delete(listener)
}

// --- core request -------------------------------------------------------------

function messageFor(status, detail) {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  if (status === 0) return 'The PARAKH server could not be reached. Check that it is running.'
  if (status === 413) return 'The file is too large.'
  if (status === 429) return 'Too many checks in a short time. Please wait a minute and try again.'
  if (status >= 500) return 'The server could not complete this request. Please try again.'
  return `Request failed (${status}).`
}

export async function request(path, { method = 'GET', json, form, auth = false, signal, raw = false } = {}) {
  if (path?.[ROUTE_CHECKED]) path = String(path)
  else assertRoute(path)
  const headers = {}
  let body
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    body = form
  }
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, { method, headers, body, signal })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError(0, messageFor(0))
  }

  if (raw && response.ok) return response
  if (response.status === 204) return null

  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = text
    }
  }

  if (!response.ok) {
    if (auth && response.status === 401) {
      setToken(null)
      authListeners.forEach((listener) => listener())
    }
    throw new ApiError(response.status, messageFor(response.status, payload?.detail), payload)
  }
  return payload
}

function query(params) {
  const search = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

function fileForm(fields) {
  const form = new FormData()
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== undefined && value !== null) form.append(key, value)
  })
  return form
}

// --- citizen API (anonymous; stores nothing unless the citizen consents) -----

export const citizenApi = {
  health: () => request('/health'),
  analyseMessage: (message, language = 'auto') =>
    request('/parakh/analyze', { method: 'POST', json: { message, language } }),
  analyseUrl: (url) => request('/parakh/url/analyze', { method: 'POST', json: { url } }),
  analyseEmail: (payload) => request('/parakh/email/analyze', { method: 'POST', json: payload }),
  extractMedia: (file, mediaKind, consent) =>
    request('/parakh/media/extract', {
      method: 'POST',
      form: fileForm({ media: file, media_kind: mediaKind, consent: String(Boolean(consent)) }),
    }),
  analyseApk: (file) => request('/parakh/apk/analyze', { method: 'POST', form: fileForm({ apk: file }) }),
  analyseQr: (payload) => request('/parakh/qr/analyze', { method: 'POST', json: { payload } }),
  checkBeforeOpen: (url) => request('/parakh/check-before-open', { method: 'POST', json: { url } }),
  rescuePlan: (payload) => request('/parakh/rescue-plan', { method: 'POST', json: payload }),
  safeNextStep: (payload) => request('/parakh/safe-next-step', { method: 'POST', json: payload }),
  explainSimply: (payload) => request('/parakh/explain-simply', { method: 'POST', json: payload }),
  verifyOrganisation: (text) => request('/parakh/organisation/verify', { method: 'POST', json: { text } }),
  trustedChannels: () => request('/parakh/trusted-channels'),
  reportToPolice: (payload) => request('/parakh/report-to-police', { method: 'POST', json: payload }),
  identifierCheck: (value) => request('/parakh/identifier/check', { method: 'POST', json: { value } }),
  meta: () => request('/parakh/meta'),
  reportStatus: (reference) => request(checked(route`/parakh/report/${reference}/status`)),
}

// --- officer API (bearer token, scoped server-side) --------------------------

export const officerApi = {
  login: (username, password) =>
    request('/investigate/auth/login', { method: 'POST', json: { username, password } }),
  logout: () => request('/investigate/auth/logout', { method: 'POST', auth: true }),
  me: () => request('/investigate/me', { auth: true }),
  dashboardSummary: (days = 30) => request(`/investigate/dashboard/summary?days=${Number(days)}`, { auth: true }),

  searchCases: (filters) => request(`/investigate/cases${query(filters)}`, { auth: true }),
  getCase: (caseId) => request(checked(route`/investigate/cases/${caseId}`), { auth: true }),
  updateCase: (caseId, patch) =>
    request(checked(route`/investigate/cases/${caseId}`), { method: 'PATCH', json: patch, auth: true }),
  linkedCases: (caseId) => request(checked(route`/investigate/cases/${caseId}/linked`), { auth: true }),
  similarCases: (caseId) => request(checked(route`/investigate/cases/${caseId}/similar`), { auth: true }),

  submit: (payload) => request('/investigate/submit', { method: 'POST', json: payload, auth: true }),
  uploadApk: (file, reporterNote) =>
    request('/investigate/apk/analyze', {
      method: 'POST',
      form: fileForm({ apk: file, reporter_note: reporterNote || undefined }),
      auth: true,
    }),
  analyseWebsite: (payload) =>
    request('/investigate/website/analyze', { method: 'POST', json: payload, auth: true }),

  identifierCases: (type, value) =>
    request(checked(route`/investigate/identifiers/${type}/cases` + query({ value })), { auth: true }),
  heatlist: (filters) => request(`/investigate/heatlist${query(filters)}`, { auth: true }),

  // --- Phase C: hierarchy, assignment, audit ---------------------------
  assignCase: (caseId, payload) =>
    request(checked(route`/investigate/cases/${caseId}/assign`), { method: 'POST', json: payload, auth: true }),
  transferCase: (caseId, payload) =>
    request(checked(route`/investigate/cases/${caseId}/transfer`), { method: 'POST', json: payload, auth: true }),
  verifyCase: (caseId) =>
    request(checked(route`/investigate/cases/${caseId}/verify`), { method: 'POST', auth: true }),
  caseAudit: (caseId) => request(checked(route`/investigate/cases/${caseId}/audit`), { auth: true }),
  auditStatus: () => request('/investigate/audit/status', { auth: true }),

  // --- Phase D: action layer -------------------------------------------
  generateActionPack: (caseId) =>
    request(checked(route`/investigate/cases/${caseId}/action-pack`), { method: 'POST', auth: true }),
  caseDocuments: (caseId) => request(checked(route`/investigate/cases/${caseId}/documents`), { auth: true }),
  getDocument: (id) => request(`/investigate/documents/${Number(id)}`, { auth: true }),
  documentPrint: (id) => request(`/investigate/documents/${Number(id)}/print`, { auth: true, raw: true }),
  editDocument: (id, bodyHtml) =>
    request(`/investigate/documents/${Number(id)}`, { method: 'PUT', json: { body_html: bodyHtml }, auth: true }),
  submitDocument: (id) => request(`/investigate/documents/${Number(id)}/submit`, { method: 'POST', auth: true }),
  approveDocument: (id, comment) =>
    request(`/investigate/documents/${Number(id)}/approve`, { method: 'POST', json: { comment: comment || null }, auth: true }),
  returnDocument: (id, comment) =>
    request(`/investigate/documents/${Number(id)}/return`, { method: 'POST', json: { comment }, auth: true }),
  dispatchDocument: (id, payload) =>
    request(`/investigate/documents/${Number(id)}/dispatch`, { method: 'POST', json: payload, auth: true }),
  recordDocumentResponse: (id, note) =>
    request(`/investigate/documents/${Number(id)}/response`, { method: 'POST', json: { note }, auth: true }),
  closeDocument: (id) => request(`/investigate/documents/${Number(id)}/close`, { method: 'POST', auth: true }),
  cancelDocument: (id, comment) =>
    request(`/investigate/documents/${Number(id)}/cancel`, { method: 'POST', json: { comment }, auth: true }),
  queue: () => request('/investigate/queue', { auth: true }),
  misReport: (period = 'weekly') => request(`/investigate/reports/mis?period=${encodeURIComponent(period)}`, { auth: true }),
  campaigns: (params) => request(`/investigate/campaigns${query(params)}`, { auth: true }),

  reportHtml: (caseId, redacted = false) =>
    request(checked(route`/investigate/cases/${caseId}/report` + query({ redacted: redacted || undefined })), {
      auth: true,
      raw: true,
    }),
  reportJson: (caseId, redacted = false) =>
    request(checked(route`/investigate/cases/${caseId}/report.json` + query({ redacted: redacted || undefined })), {
      auth: true,
      raw: true,
    }),
  exportCasesCsv: (filters) => request(`/investigate/export/cases.csv${query(filters)}`, { auth: true, raw: true }),
  exportIdentifiersCsv: (filters) =>
    request(`/investigate/export/identifiers.csv${query(filters)}`, { auth: true, raw: true }),
}

export const __test__ = { messageFor, query, BASE_URL }
