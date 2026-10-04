import { defineConfig, devices } from '@playwright/test'
import { readFileSync, existsSync } from 'node:fs'
import { parseEnv } from 'node:util'

// Keep the administrative credential outside source code and browser storage.
const envPath = '../.env'
if (!process.env.E2E_ADMIN_TOKEN && existsSync(envPath)) {
  process.env.E2E_ADMIN_TOKEN = parseEnv(
    readFileSync(envPath, 'utf8'),
  ).API_ADMIN_TOKEN
}

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 180000,
  expect: { timeout: 15000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    actionTimeout: 45000,
    baseURL: 'http://127.0.0.1:3017',
    screenshot: 'only-on-failure',
    trace: 'off',
  },
  projects: [
    {
      name: 'desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 1000 },
      },
    },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: process.env.E2E_PRODUCTION
      ? 'NITRO_PORT=3017 NITRO_HOST=127.0.0.1 node --env-file=.env.local .output/server/index.mjs'
      : 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 3017',
    url: 'http://127.0.0.1:3017',
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
})
