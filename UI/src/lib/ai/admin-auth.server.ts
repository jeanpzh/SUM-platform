export type AdminIdentity = { id: string; email: string }

export async function requireAdmin(request: Request): Promise<AdminIdentity> {
  const { auth } = await import('#/lib/auth')
  const session = await auth.api.getSession({ headers: request.headers })
  if (!session?.user) throw new Response('Se requiere iniciar sesión.', { status: 401 })
  const allowed = new Set(
    (process.env.ADMIN_EMAIL_ALLOWLIST ?? '').split(',').map((email) => email.trim().toLowerCase()).filter(Boolean),
  )
  if (session.user.role !== 'admin' || !allowed.has(session.user.email.toLowerCase()))
    throw new Response('No tienes permisos administrativos.', { status: 403 })
  return { id: session.user.id, email: session.user.email }
}
