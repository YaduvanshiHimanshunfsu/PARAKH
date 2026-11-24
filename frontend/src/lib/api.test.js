import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, assertRoute, citizenApi, officerApi, onAuthExpired, route, setToken } from './api'

function mockFetch(status = 200, body = {}) {
  const fn = vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === null ? '' : JSON.stringify(body)),
  }))
  vi.stubGlobal('fetch', fn)
  return fn
}

beforeEach(() => sessionStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('assertRoute', () => {
  it('rejects uppercase paths (defect D7: /PARAKH/media/extract returned 404)', () => {
    expect(() => assertRoute('/PARAKH/media/extract')).toThrow(/lowercase/)
  })
  it('allows uppercase only in the query string', () => {
    expect(assertRoute('/investigate/heatlist?type=UPI')).toBe('/investigate/heatlist?type=UPI')
  })
})

describe('every client call uses a lowercase /api/v1 path', () => {
  const file = new File(['x'], 'a.apk')
  const calls = [
    () => citizenApi.health(),
    () => citizenApi.analyseMessage('hi'),
    () => citizenApi.analyseUrl('a.in'),
    () => citizenApi.analyseEmail({ body: 'x' }),
    () => citizenApi.extractMedia(file, 'SCREENSHOT', true),
    () => citizenApi.analyseApk(file),
    () => citizenApi.analyseQr('upi://pay?pa=a@ybl'),
    () => citizenApi.checkBeforeOpen('a.in'),
    () => citizenApi.rescuePlan({}),
    () => citizenApi.safeNextStep({}),
    () => citizenApi.explainSimply({}),
    () => citizenApi.verifyOrganisation('x'),
    () => citizenApi.trustedChannels(),
    () => citizenApi.reportToPolice({ consent: true }),
    () => officerApi.me(),
    () => officerApi.searchCases({ q: 'x' }),
    () => officerApi.getCase('PRK-1'),
    () => officerApi.heatlist({ type: 'UPI' }),
    () => officerApi.campaigns(),
    () => officerApi.identifierCases('UPI', 'a@ybl'),
  ]
  it.each(calls.map((call, index) => [index, call]))('call %i', async (_index, call) => {
    const fetchMock = mockFetch(200, {})
    await call()
    const url = fetchMock.mock.calls[0][0]
    expect(url.startsWith('/api/v1/')).toBe(true)
    // Dynamic values (case IDs, identifier types) may be uppercase; the route text may not.
    const routeText = url.split('?')[0].replace('PRK-1', '').replace('/UPI/', '/')
    expect(routeText).toBe(routeText.toLowerCase())
  })
})

describe('route()', () => {
  it('encodes values and keeps their case', () => {
    expect(route`/investigate/identifiers/${'UPI'}/cases`).toBe('/investigate/identifiers/UPI/cases')
    expect(route`/investigate/cases/${'PRK 1/x'}`).toBe('/investigate/cases/PRK%201%2Fx')
  })
  it('rejects uppercase in the fixed route text', () => {
    expect(() => route`/Investigate/cases/${'PRK-1'}`).toThrow(/lowercase/)
  })
})

describe('request behaviour', () => {
  it('sends JSON and returns the parsed body', async () => {
    const fetchMock = mockFetch(200, { verdict: 'SCAM' })
    const result = await citizenApi.analyseMessage('Pay now', 'hi')
    expect(result).toEqual({ verdict: 'SCAM' })
    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('POST')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ message: 'Pay now', language: 'hi' })
  })

  it('maps server detail into ApiError', async () => {
    mockFetch(422, { detail: 'Consent is required before media can be processed.' })
    await expect(citizenApi.extractMedia(new File(['x'], 'a.png'), 'SCREENSHOT', false)).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      message: 'Consent is required before media can be processed.',
    })
  })

  it('reports network failure as status 0 with a helpful message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    const error = await citizenApi.health().catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(0)
    expect(error.isUnavailable).toBe(true)
  })

  it('attaches the officer token and clears it on 401', async () => {
    setToken('secret-token')
    const listener = vi.fn()
    const off = onAuthExpired(listener)
    const fetchMock = mockFetch(401, { detail: 'Session is invalid or has expired.' })
    await expect(officerApi.me()).rejects.toMatchObject({ status: 401 })
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer secret-token')
    expect(sessionStorage.getItem('parakh.officer.token')).toBeNull()
    expect(listener).toHaveBeenCalledOnce()
    off()
  })

  it('never sends a token on citizen calls', async () => {
    setToken('secret-token')
    const fetchMock = mockFetch(200, {})
    await citizenApi.analyseUrl('a.in')
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined()
  })
})
