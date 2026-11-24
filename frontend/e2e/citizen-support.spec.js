import { expect, test } from '@playwright/test'

// H.3 screens with the API mocked (bodies follow app/schemas.py).

const API = '**/api/v1'

async function mockJson(page, path, body, capture, status = 200) {
  await page.route(`${API}${path}`, async (route) => {
    capture?.push(route.request().postDataJSON?.() ?? null)
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  })
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

test('rescue plan follows what the citizen says happened', async ({ page }) => {
  const asked = []
  await mockJson(
    page,
    '/parakh/rescue-plan',
    {
      urgency: 'CRITICAL',
      title: 'Money sent: report within the golden hour',
      actions: [
        { priority: 2, instruction: 'Call your bank using the number on your card and ask to block the account.', official_url: null },
        { priority: 1, instruction: 'Call 1930 now and report the transaction ID.', official_url: 'https://cybercrime.gov.in/' },
      ],
      evidence_to_preserve: ['Transaction ID / UTR number'],
      limitations: ['This plan does not replace a police complaint.'],
    },
    asked,
  )
  await page.goto('/rescue?exposure=SENT_MONEY&verdict=SCAM&category=UPI_FRAUD')
  await expect(page.getByText('Act now — the first hours matter most')).toBeVisible()
  // Steps are shown in priority order, not response order.
  await expect(page.getByText(/^Step 1$/).locator('..')).toContainText('Call 1930 now')
  await page.getByLabel('Mark step 1 done').check()
  await expect(page.getByText('1 / 2 done')).toBeVisible()
  expect(asked[0]).toEqual({ exposure_state: 'SENT_MONEY', verdict: 'SCAM', scam_category: 'UPI_FRAUD' })
  await expectNoOverflow(page, 'rescue')
})

test('help page verifies an organisation claim and lists official channels', async ({ page }) => {
  await mockJson(page, '/parakh/trusted-channels', [
    { category: 'Financial cyber fraud', title: 'National Cyber Crime Reporting Portal', official_url: 'https://cybercrime.gov.in/', phone: '1930', instruction: 'For a suspected financial cyber-fraud loss, call 1930 promptly.' },
  ])
  await mockJson(page, '/parakh/organisation/verify', {
    claims: [
      {
        claimed_organisation: 'State Bank of India',
        official_domains: ['sbi.co.in', 'onlinesbi.sbi'],
        safe_instruction: 'Open the YONO app yourself or call the number on your card.',
        risk_reason: 'The message uses a domain that SBI does not own.',
      },
    ],
    notice: 'Official domains come from PARAKH’s reviewed list.',
  })
  await page.goto('/help')
  await expect(page.getByRole('heading', { name: 'National Cyber Crime Reporting Portal' })).toBeVisible()
  await page.getByRole('button', { name: /Try a practice sample/ }).click()
  await page.getByRole('button', { name: 'Verify' }).click()
  await expect(page.getByText('sbi.co.in')).toBeVisible()
  await expect(page.getByText('The message uses a domain that SBI does not own.')).toBeVisible()
  await expectNoOverflow(page, 'help')
})

test('learn page sends an example to the checker without putting it in the URL', async ({ page }) => {
  await page.goto('/learn')
  await page.getByRole('radio', { name: /Jobs & investment/ }).check({ force: true })
  await expect(page.getByRole('heading', { name: 'Part-time task / rating jobs' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Electricity bill disconnection' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Check this example' }).first().click()
  await expect(page).toHaveURL(/\/check\?mode=message$/)
  await expect(page.getByLabel(/Paste the message/)).toHaveValue(/Earn Rs 3,000 daily/)
})

test('learn quiz scores answers and can ask the real analyser', async ({ page }) => {
  await mockJson(page, '/parakh/analyze', {
    verdict: 'SCAM', confidence: 88, scam_category: 'UTILITY_BILL_SCAM', severity: 'HIGH', psychological_tactics: [],
    red_flags: [], action_steps: ['Do not call.'], hindi_summary: 'ठगी', analysis_source: 'RULE_FALLBACK', url_analyses: [],
  })
  await page.goto('/learn')
  await page.getByRole('button', { name: 'Scam', exact: true }).click()
  await expect(page.getByText('Correct.')).toBeVisible()
  await expect(page.getByText('Score 1 / 1')).toBeVisible()
  await page.getByRole('button', { name: /Ask PARAKH’s analyser/ }).click()
  await expect(page.getByText('Electricity or utility bill scam')).toBeVisible()
})

test('evidence locker saves, shows and deletes an encrypted item', async ({ page }) => {
  await page.goto('/evidence')
  await expect(page.getByText('Nothing saved yet')).toBeVisible()
  await page.getByLabel('Details').fill('UTR 412345678901 · Rs 5,000 to richplan@ybl')
  await page.getByLabel('Note (optional)').fill('Paid at 4:10 PM')
  await page.getByRole('button', { name: 'Save encrypted' }).click()
  await expect(page.getByText('Paid at 4:10 PM')).toBeVisible()

  // Stored ciphertext must not contain the plaintext.
  const raw = await page.evaluate(
    () =>
      new Promise((resolve) => {
        const open = indexedDB.open('parakh-evidence-vault')
        open.onsuccess = () => {
          const read = open.result.transaction('evidence').objectStore('evidence').getAll()
          read.onsuccess = () => resolve(JSON.stringify(read.result.map((r) => [...new Uint8Array(r.encrypted)])))
        }
      }),
  )
  expect(raw).not.toContain('richplan')

  await page.getByRole('button', { name: 'View' }).click()
  await expect(page.getByRole('dialog')).toContainText('UTR 412345678901')
  await page.getByRole('button', { name: 'Delete' }).click()
  await expect(page.getByText('Nothing saved yet')).toBeVisible()
})

test('report status shows the stage and handles unknown references', async ({ page }) => {
  await mockJson(page, '/parakh/report/PRK-20261124-ABC234/status', {
    reference: 'PRK-20261124-ABC234', status: 'UNDER_REVIEW', artifact_type: 'MESSAGE',
    received_at: '2026-11-24T06:00:00+00:00', updated_at: '2026-11-24T08:30:00+00:00',
  })
  await mockJson(page, '/parakh/report/PRK-20261124-ZZZZZZ/status', { detail: 'No citizen report has this reference.' }, null, 404)
  await page.goto('/status/prk-20261124-abc234')
  await expect(page.getByText('An officer is reviewing your report')).toBeVisible()
  await expect(page.getByRole('list', { name: 'Report progress' }).locator('[aria-current="step"]')).toContainText('Under review')

  await page.getByLabel('Report reference').fill('PRK-20261124-ZZZZZZ')
  await page.getByRole('button', { name: 'Track' }).click()
  await expect(page.getByText('No report found with this reference')).toBeVisible()
})

test('privacy page states the AI setting of this server', async ({ page }) => {
  await mockJson(page, '/parakh/meta', { rule_count: 120, scam_categories: [], ai_configured: false, offline_fallback: true, version: '1.0.0' })
  await page.goto('/privacy')
  await expect(page.getByText(/AI service switched off/)).toBeVisible()
})
