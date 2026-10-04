import { betterAuth } from 'better-auth'
import { admin } from 'better-auth/plugins'
import { tanstackStartCookies } from 'better-auth/tanstack-start'
import { Pool } from 'pg'

if (!process.env.AUTH_DATABASE_URL || !process.env.BETTER_AUTH_SECRET || process.env.BETTER_AUTH_SECRET.length < 32)
  throw new Error('Configure AUTH_DATABASE_URL y BETTER_AUTH_SECRET (mínimo 32 caracteres).')

export const authDatabase = new Pool({
  connectionString: process.env.AUTH_DATABASE_URL,
  max: 5,
  connectionTimeoutMillis: 3000,
  idleTimeoutMillis: 30000,
})

export const auth = betterAuth({
  database: authDatabase,
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL,
  trustedOrigins: (process.env.BETTER_AUTH_TRUSTED_ORIGINS ?? '').split(',').map((value) => value.trim()).filter(Boolean),
  emailAndPassword: {
    enabled: true,
    disableSignUp: true,
  },
  plugins: [admin(), tanstackStartCookies()],
})
