import { expect, test } from '@playwright/test'

// Citizen flows against the static preview with the API mocked at the network
// layer. Response bodies follow app/schemas.py exactly; the live-backend run
// (PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000) exercises the real analysers.

const API = '**/api/v1'

const MESSAGE_RESULT = {
  verdict: 'SCAM',
  confidence: 92,
  scam_category: 'UTILITY_BILL_SCAM',
  severity: 'HIGH',
  psychological_tactics: ['FALSE_URGENCY', 'FEAR_INDUCTION'],
  red_flags: [
    { phrase: 'disconnected tonight', explanation: 'A same-night deadline is used to rush you.' },
    { phrase: '9988776655', explanation: 'Discoms never ask you to call a private mobile number.' },
  ],
  action_steps: ['Do not call the number.', 'Check your bill on the official discom portal.'],
  hindi_summary: 'यह बिजली बिल ठगी है। नंबर पर कॉल न करें।',
  safe_explanation: null,
  analysis_source: 'RULE_FALLBACK',
  model_used: null,
  notice: null,
  url_analyses: [],
}

const URL_RESULT = {
  original_url: 'https://sbi-verify-kyc.in/urgent',
  normalized_url: 'https://sbi-verify-kyc.in/urgent',
  host: 'sbi-verify-kyc.in',
  registered_domain: 'sbi-verify-kyc.in',
  risk_level: 'HIGH',
  risk_score: 84,
  signals: [{ code: 'BRAND_IN_UNOFFICIAL_DOMAIN', severity: 'HIGH', explanation: 'Uses a bank name on a domain the bank does not own.' }],
  tls: { status: 'NOT_CHECKED', issuer: null, expires_at: null, hostname_verified: null },
  reputation: [],
  site_profile: null,
  summary: 'This link imitates a bank and is likely a phishing page.',
  limitations: 'The page itself was not opened or downloaded.',
}

const APK_RESULT = {
  risk_level: 'HIGH',
  risk_score: 90,
  summary: 'This app asks to read SMS and is signed with a test certificate.',
  findings: [
    { code: 'DEBUG_CERTIFICATE', severity: 'HIGH', explanation: 'Signed with an Android debug certificate.', evidence: 'CN=Android Debug' },
  ],
  identifiers: [{ type: 'UPI', value: 'richplan@ybl', raw_value: 'richplan@ybl', context: null, confidence: 100 }],
  details: {
    filename: 'RTO_Challan.apk',
    package: 'com.rto.challan',
    app_label: 'RTO Challan',
    size_bytes: 120000,
    permission_profile: [
      { name: 'android.permission.READ_SMS', short: 'READ_SMS', category: 'SMS', level: 'DANGEROUS', description: 'Read your text messages, including OTPs.' },
      { name: 'android.permission.INTERNET', short: 'INTERNET', category: 'Network', level: 'NORMAL', description: 'Use the internet.' },
    ],
    certificate: { subject: 'CN=Android Debug', debug_certificate: true, self_signed: true },
    limitations: ['Code was not decompiled.'],
  },
  reported_identifiers: [{ type: 'UPI', value: 'richplan@ybl', case_count: 4 }],
  advice: ['Do not install this app.'],
  helpline: '1930',
  official_portal: 'https://cybercrime.gov.in/',
}

async function expectNoOverflow(page, shot) {
  await page.evaluate(() => document.fonts.ready)
  const offenders = await page.evaluate(() =>
    [...document.querySelectorAll('body *')]
      .filter((el) => {
        const box = el.getBoundingClientRect()
        if (box.width === 0 || box.right <= window.innerWidth + 1) return false
        for (let parent = el.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
          if (['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(parent).overflowX)) return false
        }
        return true
      })
      .map((el) => `${el.tagName.toLowerCase()} "${(el.textContent || '').trim().slice(0, 30)}"`)
      .slice(0, 5),
  )
  expect(offenders).toEqual([])
  if (shot && process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${shot}-${test.info().project.name}.png`, fullPage: true })
}

async function mockJson(page, path, body, capture) {
  await page.route(`${API}${path}`, async (route) => {
    capture?.push(route.request().postDataJSON?.() ?? null)
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
}

test('home quick-check runs a real request and shows the verdict with highlights', async ({ page }) => {
  const sent = []
  await mockJson(page, '/parakh/analyze', MESSAGE_RESULT, sent)
  await page.goto('/')
  await page.getByLabel(/Paste a suspicious message or link/).fill('Your power will be disconnected tonight. Call 9988776655')
  await expect(page.getByLabel('Detected in your text')).toContainText('9988776655')
  await page.getByRole('button', { name: /Check now/ }).click()

  await expect(page).toHaveURL(/\/result$/)
  await expect(page.getByRole('heading', { name: 'This looks like a scam' })).toBeVisible()
  await expect(page.locator('mark', { hasText: 'disconnected tonight' })).toBeVisible()
  await expect(page.getByText('Electricity or utility bill scam')).toBeVisible()
  await expect(page.getByText(/offline rules/)).toBeVisible()
  await expectNoOverflow(page, 'result-message')
  expect(sent[0]).toEqual({ message: 'Your power will be disconnected tonight. Call 9988776655', language: 'auto' })
})

test('a pasted link goes to the URL analyser, not the message analyser', async ({ page }) => {
  await mockJson(page, '/parakh/url/analyze', URL_RESULT)
  await page.goto('/check?mode=link')
  await page.getByLabel(/Check a link before you open it/).fill('https://sbi-verify-kyc.in/urgent')
  await page.getByRole('button', { name: 'Check link' }).click()
  await expect(page.getByRole('heading', { name: 'This looks like a scam' })).toBeVisible()
  await expect(page.getByText('BRAND_IN_UNOFFICIAL_DOMAIN')).toBeVisible()
  await expect(page.getByRole('img', { name: /High risk: 84 out of 100/ })).toBeVisible()
  await expectNoOverflow(page, 'result-url')
})

test('report to police is blocked until the citizen consents', async ({ page }) => {
  const reports = []
  await mockJson(page, '/parakh/analyze', MESSAGE_RESULT)
  await page.route(`${API}/parakh/report-to-police`, async (route) => {
    reports.push(route.request().postDataJSON())
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ reference: 'PRK-CIT-7Q2M', message: 'Thank you. Officers will review this report.', helpline: '1930', official_portal: 'https://cybercrime.gov.in/' }),
    })
  })
  await page.goto('/check')
  await page.getByLabel(/Paste the message/).fill('Your power will be disconnected tonight. Call 9988776655')
  await page.getByRole('button', { name: /Analyse message/ }).click()

  const send = page.getByRole('button', { name: 'Send to police' })
  await expect(send).toBeDisabled()
  await page.getByLabel(/I agree this content is stored for police review/).check()
  await send.click()
  await expect(page.getByText('PRK-CIT-7Q2M')).toBeVisible()
  await expect(page.getByText(/This is not an FIR/)).toBeVisible()
  expect(reports).toHaveLength(1)
  expect(reports[0]).toMatchObject({ artifact_type: 'MESSAGE', consent: true })
})

test('safe-next-step answers for the chosen action', async ({ page }) => {
  await mockJson(page, '/parakh/analyze', MESSAGE_RESULT)
  const asked = []
  await mockJson(
    page,
    '/parakh/safe-next-step',
    {
      decision: 'STOP_NOW',
      title: 'Do not call this number',
      simple_explanation: 'The number in this message belongs to the scammer.',
      hindi_explanation: 'इस नंबर पर कॉल न करें।',
      hinglish_explanation: 'Is number par call mat karo.',
      steps: ['Use the number printed on your bill.'],
    },
    asked,
  )
  await page.goto('/check')
  await page.getByLabel(/Paste the message/).fill('Your power will be disconnected tonight. Call 9988776655')
  await page.getByRole('button', { name: /Analyse message/ }).click()
  await page.getByRole('button', { name: 'Call the number' }).click()
  await expect(page.getByText('Do not call this number')).toBeVisible()
  expect(asked[0]).toMatchObject({ action: 'CALL_NUMBER', verdict: 'SCAM', scam_category: 'UTILITY_BILL_SCAM', exposure_state: 'RECEIVED_ONLY' })
})

test('UPI identifier check shows police-case count', async ({ page }) => {
  await mockJson(page, '/parakh/identifier/check', {
    input: 'richplan@ybl',
    type: 'UPI',
    value: 'richplan@ybl',
    risk_level: 'HIGH',
    reported_case_count: 4,
    blacklisted: false,
    blacklist_source: null,
    advice: ['Do not pay this UPI ID.'],
    limitations: 'Only officer-verified high-risk cases and the reviewed blacklist are searched.',
  })
  await page.goto('/check?mode=identifier')
  await page.getByLabel(/Check a UPI ID, phone number or website/).fill('richplan@ybl')
  await page.getByRole('button', { name: 'Check', exact: true }).click()
  await expect(page.getByText(/appears in 4 officer-verified high-risk cases/)).toBeVisible()
  await expectNoOverflow(page, 'result-identifier')
})

test('APK check shows permissions, certificate and prior police cases', async ({ page }) => {
  await mockJson(page, '/parakh/apk/analyze', APK_RESULT)
  await page.goto('/apk')
  await page.locator('input[type=file]').setInputFiles({ name: 'RTO_Challan.apk', mimeType: 'application/vnd.android.package-archive', buffer: Buffer.from('PK\u0003\u0004fake') })
  await expect(page.getByRole('heading', { name: 'Do not install this app' })).toBeVisible()
  await expect(page.getByText('Already seen in police cases')).toBeVisible()
  await expect(page.getByText('READ_SMS')).toBeVisible()
  await expect(page.getByText('com.rto.challan')).toBeVisible()
  await expectNoOverflow(page, 'apk')
})

test('result page without a result explains why', async ({ page }) => {
  await page.goto('/result')
  await expect(page.getByRole('heading', { name: 'No result to show' })).toBeVisible()
})

test('API errors are shown, not swallowed', async ({ page }) => {
  await page.route(`${API}/parakh/analyze`, (route) =>
    route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Analysis is temporarily unavailable.' }) }),
  )
  await page.goto('/check')
  await page.getByLabel(/Paste the message/).fill('hello there friend')
  await page.getByRole('button', { name: /Analyse message/ }).click()
  await expect(page.getByText('The check could not be completed.')).toBeVisible()
})
