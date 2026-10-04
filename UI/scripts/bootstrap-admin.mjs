import { auth, authDatabase } from '../src/lib/auth.ts'

const email = process.env.ADMIN_BOOTSTRAP_EMAIL?.trim().toLowerCase()
const password = process.env.ADMIN_BOOTSTRAP_PASSWORD
const allowed = (process.env.ADMIN_EMAIL_ALLOWLIST ?? '').split(',').map((value) => value.trim().toLowerCase())
try {
  if (!email || !allowed.includes(email) || !password || password.length < 12)
    throw new Error('Configure un correo de ADMIN_EMAIL_ALLOWLIST y ADMIN_BOOTSTRAP_PASSWORD de al menos 12 caracteres.')
  await auth.api.createUser({ body: { email, password, name: process.env.ADMIN_BOOTSTRAP_NAME || 'Administrador SUM', role: 'admin' } })
  console.log('Administrador creado. El registro público está deshabilitado.')
} catch {
  console.error('No se pudo crear el administrador. Revise configuración y si el correo ya existe.')
  process.exitCode = 1
} finally {
  await authDatabase.end()
}
