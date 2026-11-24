import { expect, test } from '@playwright/test'

// H.0 shell checks. The most important assertion is offline-safety: the app
// must never request anything outside its own origin (no CDN, no Google Fonts,
// no hot-linked images), or the demo breaks without Wi-Fi.

test.beforeEach(async ({ page }, testInfo) => {
  const external = []
  const consoleErrors = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (!['127.0.0.1', 'localhost'].includes(url.hostname) && url.protocol.startsWith('http')) external.push(request.url())
  })
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  testInfo.external = external
  testInfo.consoleErrors = consoleErrors
})

test.afterEach(async ({}, testInfo) => {
  expect(testInfo.external, 'requests left the local origin').toEqual([])
  // /api calls fail in the static preview (no backend); ignore only those.
  expect(testInfo.consoleErrors.filter((text) => !text.includes('/api/'))).toEqual([])
})

test('citizen shell renders with brand, helpline and language toggle', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'PARAKH home' })).toBeVisible()
  const helpline = page.getByRole('link', { name: 'Call the National Cyber Crime Helpline 1930' })
  await expect(helpline).toHaveAttribute('href', 'tel:1930')

  await page.getByRole('button', { name: 'हिं' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'hi')
  await page.getByRole('button', { name: 'EN' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')

  if (testInfo.project.name === 'mobile') {
    await expect(page.getByRole('navigation', { name: 'Quick navigation' })).toBeVisible()
  } else {
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
  }
})

test('unbuilt screens say so honestly', async ({ page }) => {
  await page.goto('/check')
  await expect(page.getByText('This screen is being built')).toBeVisible()
})

test('officer routes require sign-in', async ({ page }) => {
  await page.goto('/investigate')
  await expect(page).toHaveURL(/\/investigate\/login$/)
})

test('dev-only states gallery is not in the production build', async ({ page }) => {
  await page.goto('/__states')
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
})

// Every visible element must fit inside the viewport (not just the document),
// checked after web fonts load so icon ligatures have their real width.
for (const path of ['/', '/check', '/apk', '/rescue', '/help', '/learn', '/evidence', '/investigate/login', '/no-such-page']) {
  test(`no element overflows the viewport on ${path}`, async ({ page }) => {
    await page.goto(path)
    await page.evaluate(() => document.fonts.ready)
    const offenders = await page.evaluate(() =>
      [...document.querySelectorAll('body *')]
        .filter((el) => {
          const box = el.getBoundingClientRect()
          return box.width > 0 && box.right > window.innerWidth + 1
        })
        .map((el) => `${el.tagName.toLowerCase()} "${(el.textContent || '').trim().slice(0, 30)}"`)
        .slice(0, 5),
    )
    expect(offenders).toEqual([])
  })
}
