import { expect, test } from '@playwright/test'

// Officer console with the API mocked (bodies follow app/schemas.py).
// The live-backend run exercises the real services.

const API = '**/api/v1'
const NOW = new Date().toISOString()
const day = (offset) => new Date(Date.now() - offset * 86_400_000).toISOString().slice(0, 10)

const summary = (id, risk = 'HIGH', extra = {}) => ({
  case_id: id,
  artifact_type: 'MESSAGE',
  risk_level: risk,
  risk_score: risk === 'HIGH' ? 88 : 45,
  status: 'NEW',
  source: 'OFFICER',
  summary: 'Ponzi scheme promising guaranteed daily returns.',
  preview: `RichPlan Investment: ${'Guaranteed 10% daily returns, referral bonus on every downline member. '.repeat(4)}`.slice(0, 300),
  identifier_count: 2,
  finding_count: 3,
  created_at: NOW,
  ...extra,
})

const CASE_A = 'PRK-20261124-AAAAAA'
const CASE_B = 'PRK-20261124-BBBBBB'

async function json(page, path, body, status = 200) {
  await page.route(`${API}${path}`, (route) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) }))
}

async function signIn(page) {
  await json(page, '/investigate/auth/login', { token: 'x'.repeat(40), username: 'test_officer', role: 'OFFICER', expires_at: NOW })
  await json(page, '/investigate/me', { username: 'test_officer', role: 'OFFICER' })
  await page.goto('/investigate/login')
  await page.getByLabel('Username').fill('test_officer')
  await page.getByLabel('Password', { exact: true }).fill('InvestigationPass123')
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function expectNoOverflow(page) {
  await page.evaluate(() => document.fonts.ready)
  const offenders = await page.evaluate(() =>
    [...document.querySelectorAll('body *')]
      .filter((el) => {
        const box = el.getBoundingClientRect()
        if (box.width === 0 || box.right <= window.innerWidth + 1) return false
        if (el.closest('aside')) return false // off-canvas sidebar on mobile
        for (let parent = el.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
          if (['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(parent).overflowX)) return false
        }
        return true
      })
      .map((el) => `${el.tagName.toLowerCase()} "${(el.textContent || '').trim().slice(0, 30)}"`)
      .slice(0, 5),
  )
  expect(offenders).toEqual([])
}

test('wrong password shows a clear error', async ({ page }) => {
  await json(page, '/investigate/auth/login', { detail: 'Invalid credentials' }, 401)
  await page.goto('/investigate/login')
  await page.getByLabel('Username').fill('someone')
  await page.getByLabel('Password', { exact: true }).fill('wrongpassword')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByText('Wrong username or password.')).toBeVisible()
})

test('dashboard shows numbers from the summary endpoint', async ({ page }) => {
  const requested = []
  await page.route(`${API}/investigate/dashboard/summary*`, (route) => {
    requested.push(new URL(route.request().url()).searchParams.get('days'))
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        days: 30,
        generated_at: NOW,
        total_cases: 57,
        cases_in_period: 41,
        high_risk_in_period: 19,
        new_today: 3,
        citizen_reports_new: 4,
        unreviewed: 12,
        campaigns: 5,
        artifact_mix: { MESSAGE: 30, URL: 6, APK: 5 },
        risk_mix: { HIGH: 19, MEDIUM: 14, LOW: 8 },
        series: Array.from({ length: 30 }, (_, i) => ({ date: day(29 - i), high: i % 3, medium: i % 2, low: 1 })),
        recent_cases: [summary(CASE_A)],
      }),
    })
  })
  await signIn(page)
  await expect(page).toHaveURL(/\/investigate$/)
  await expect(page.getByRole('heading', { name: 'Command dashboard' })).toBeVisible()
  await expect(page.locator('div', { has: page.getByText('Cases · 30 days') }).getByText('41', { exact: true }).last()).toBeVisible()
  await expect(page.getByRole('img', { name: 'Cases by risk level in this period' })).toContainText('41')
  await expect(page.getByText('19', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('img', { name: /Cases per day by risk level/ })).toBeVisible()
  await page.getByRole('button', { name: 'Show table' }).click()
  await expect(page.getByRole('table')).toContainText(day(0))
  await page.getByRole('radio', { name: '7 days' }).check({ force: true })
  await expect.poll(() => requested).toContain('7')
  await expectNoOverflow(page)
})

test('cases table filters through the URL and opens a case dossier', async ({ page }) => {
  const queries = []
  await page.route(`${API}/investigate/cases?*`, (route) => {
    queries.push(new URL(route.request().url()).search)
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ total: 1, limit: 25, offset: 0, cases: [summary(CASE_A)] }) })
  })
  await json(page, `/investigate/cases/${CASE_A}`, {
    ...summary(CASE_A),
    content_text: 'RichPlan Investment: Guaranteed 10% daily returns! Pay richplan@ybl',
    reporter_note: 'Walk-in complaint',
    officer_note: null,
    findings: [{ code: 'GUARANTEED_RETURNS', severity: 'HIGH', explanation: 'Promises guaranteed daily returns.', evidence: 'Guaranteed 10% daily returns' }],
    identifiers: [{ type: 'UPI', value: 'richplan@ybl', raw_value: 'richplan@ybl', context: null, confidence: 100 }],
    details: {},
  })
  await json(page, `/investigate/cases/${CASE_A}/linked`, [{ case: summary(CASE_B), shared_identifiers: ['richplan@ybl'], link_strength: 80 }])
  await json(page, `/investigate/cases/${CASE_A}/similar`, [])

  await signIn(page)
  await page.goto('/investigate/cases')
  await page.getByLabel('Risk level').selectOption('HIGH')
  await expect(page).toHaveURL(/risk_level=HIGH/)
  await expect.poll(() => queries.some((q) => q.includes('risk_level=HIGH'))).toBe(true)

  await page.getByRole('link', { name: CASE_A }).click()
  await expect(page.getByRole('heading', { name: CASE_A })).toBeVisible()
  await expect(page.locator('mark', { hasText: 'Guaranteed 10% daily returns' })).toBeVisible()
  await expect(page.getByText('Walk-in complaint')).toBeVisible()
  await expect(page.getByText(CASE_B)).toBeVisible()
  await expect(page.getByText('No near-duplicate text found')).toBeVisible()
  await expectNoOverflow(page)
})

test('saving a case status sends a PATCH', async ({ page }) => {
  const patches = []
  const detail = {
    ...summary(CASE_A), content_text: 'x', reporter_note: null, officer_note: null, findings: [], identifiers: [], details: {},
  }
  await page.route(`${API}/investigate/cases/${CASE_A}`, (route) => {
    if (route.request().method() === 'PATCH') {
      const body = route.request().postDataJSON()
      patches.push(body)
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...detail, ...body }) })
    }
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify(detail) })
  })
  await json(page, `/investigate/cases/${CASE_A}/linked`, [])
  await json(page, `/investigate/cases/${CASE_A}/similar`, [])
  await signIn(page)
  await page.goto(`/investigate/case/${CASE_A}`)
  await page.getByLabel('Status').selectOption('UNDER_REVIEW')
  await page.getByLabel('Officer note').fill('Bank freeze requested')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByText('Case updated.')).toBeVisible()
  expect(patches[0]).toEqual({ status: 'UNDER_REVIEW', officer_note: 'Bank freeze requested' })
})

test('campaign map draws the network and opens the timeline', async ({ page }) => {
  await json(page, '/investigate/campaigns', {
    campaigns: [
      {
        campaign_id: 'cmp-1',
        name: 'RichPlan Ponzi',
        case_count: 2,
        risk_level: 'HIGH',
        artifact_mix: { MESSAGE: 2 },
        first_seen: NOW,
        last_seen: NOW,
        key_identifiers: [{ type: 'UPI', value: 'richplan@ybl', case_count: 2 }],
        timeline: [
          { case_id: CASE_A, created_at: NOW, artifact_type: 'MESSAGE', risk_level: 'HIGH', summary: 's', preview: 'First version', variant_of: null, similarity: null, changes: [], new_identifiers: ['richplan@ybl'] },
          { case_id: CASE_B, created_at: NOW, artifact_type: 'MESSAGE', risk_level: 'HIGH', summary: 's', preview: 'Second version', variant_of: CASE_A, similarity: 91, changes: [{ before: '10%', after: '12%' }], new_identifiers: [] },
        ],
      },
    ],
    nodes: [
      { id: `case:${CASE_A}`, kind: 'case', label: 'First', campaign_id: 'cmp-1', case_id: CASE_A, artifact_type: 'MESSAGE', risk_level: 'HIGH' },
      { id: `case:${CASE_B}`, kind: 'case', label: 'Second', campaign_id: 'cmp-1', case_id: CASE_B, artifact_type: 'MESSAGE', risk_level: 'HIGH' },
      { id: 'id:UPI:richplan@ybl', kind: 'identifier', label: 'richplan@ybl', campaign_id: 'cmp-1', identifier_type: 'UPI', value: 'richplan@ybl', case_count: 2 },
    ],
    edges: [
      { source: `case:${CASE_A}`, target: 'id:UPI:richplan@ybl', kind: 'identifier', weight: 100 },
      { source: `case:${CASE_B}`, target: 'id:UPI:richplan@ybl', kind: 'identifier', weight: 100 },
      { source: `case:${CASE_A}`, target: `case:${CASE_B}`, kind: 'similar', weight: 91 },
    ],
    cases_scanned: 10,
    linked_case_count: 2,
  })
  await signIn(page)
  await page.goto('/investigate/campaigns')
  await expect(page.getByText('2 of 10 cases are linked into 1 campaign')).toBeVisible()
  await expect(page.getByRole('button', { name: /UPI richplan@ybl, in 2 cases/ })).toBeVisible()
  await page.getByRole('button', { name: /RichPlan Ponzi/ }).click()
  await expect(page.getByText('Variant of')).toBeVisible()
  await expect(page.getByText('12%')).toBeVisible()
  await expectNoOverflow(page)
})

test('heat-list shows week-on-week trend and pivots to the identifier', async ({ page }) => {
  await page.route(`${API}/investigate/heatlist*`, (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([
        { type: 'UPI', value: 'richplan@ybl', case_count: 9, recent_case_count: 6, previous_case_count: 3, first_seen: NOW, last_seen: NOW },
        { type: 'PHONE', value: '+919812345670', case_count: 4, recent_case_count: 2, previous_case_count: 0, first_seen: NOW, last_seen: NOW },
      ]),
    }),
  )
  await page.route(`${API}/investigate/identifiers/UPI/cases*`, (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ total: 2, limit: 50, offset: 0, cases: [summary(CASE_A), summary(CASE_B, 'MEDIUM', { source: 'CITIZEN' })] }) }),
  )
  await signIn(page)
  await page.goto('/investigate/heatlist')
  await expect(page.getByText('+100% vs last week')).toBeVisible()
  await expect(page.getByText('New this week')).toBeVisible()
  await page.getByRole('link', { name: /richplan@ybl/ }).click()
  await expect(page).toHaveURL(/\/investigate\/identifier\/UPI\/richplan%40ybl$/)
  await expect(page.getByRole('heading', { name: '2 cases, oldest first' })).toBeVisible()
  await expectNoOverflow(page)
})
