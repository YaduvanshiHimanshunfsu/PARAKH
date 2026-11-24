import { defineConfig, devices } from '@playwright/test'

// E2E runs against the production build (vite preview). Flows that need the
// API run against FastAPI by setting PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000.
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:4300' },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : { command: 'npm run build && npm run preview -- --host 127.0.0.1 --port 4300', port: 4300, reuseExistingServer: true },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 5'], viewport: { width: 390, height: 844 } } },
  ],
})
