import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'node:path'
import { devtools } from '@tanstack/devtools-vite'

import { tanstackStart } from '@tanstack/react-start/plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { nitro } from 'nitro/vite'

const config = defineConfig(({ mode }) => {
  // Reuse Compose's local configuration without exposing it via VITE_ or define.
  if (mode === 'development' || mode === 'test') {
    const shared: Partial<Record<string, string>> = loadEnv(
      mode,
      resolve(import.meta.dirname, '..'),
      '',
    )
    const local: Partial<Record<string, string>> = loadEnv(
      mode,
      import.meta.dirname,
      '',
    )
    const token =
      process.env.API_ADMIN_TOKEN ??
      local.BACKEND_ADMIN_TOKEN ??
      shared.BACKEND_ADMIN_TOKEN ??
      shared.API_ADMIN_TOKEN
    if (token) process.env.BACKEND_ADMIN_TOKEN ??= token
    const url = local.BACKEND_API_URL ?? shared.BACKEND_API_URL
    if (url) process.env.BACKEND_API_URL ??= url
    for (const key of ['AUTH_DATABASE_URL', 'BETTER_AUTH_SECRET', 'BETTER_AUTH_URL', 'BETTER_AUTH_TRUSTED_ORIGINS', 'AI_IDENTITY_SECRET', 'ADMIN_EMAIL_ALLOWLIST']) {
      const value = local[key] ?? shared[key]
      if (value) process.env[key] ??= value
    }
  }
  return {
    resolve: { tsconfigPaths: true },
    server: {
      watch: {
        ignored: [
          '**/playwright-report/**',
          '**/test-results/**',
          '**/pdf-ingestion/qa/**',
        ],
      },
    },
    plugins: [devtools(), nitro(), tailwindcss(), tanstackStart(), viteReact()],
  }
})

export default config
