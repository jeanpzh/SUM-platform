import { useEffect, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { authClient } from '#/lib/auth-client'

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>) => ({
    mode: search.mode === 'student' ? ('student' as const) : ('admin' as const),
  }),
  component: Login,
})

function Login() {
  const { mode } = Route.useSearch()
  const student = mode === 'student'
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [ready, setReady] = useState(false)
  useEffect(() => setReady(true), [])
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      const result = await authClient.signIn.email({ email, password })
      if (result.error) setError('No se pudo iniciar sesión.')
      else await navigate({ to: student ? '/assistant' : '/admin/chat' })
    } catch {
      setError('No se pudo iniciar sesión.')
    } finally {
      setPending(false)
    }
  }
  return (
    <main className="student-login mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <h1 className="font-display text-3xl font-semibold">
        {student ? 'Tu espacio académico' : 'Administración SUM'}
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        {student
          ? 'Ingresa para consultar al asistente y ver tu historial.'
          : 'Ingresa con tu cuenta administrativa.'}
      </p>
      <form onSubmit={submit} className="mt-8 grid gap-4">
        <label className="grid gap-1 text-sm">
          Correo
          <input
            className="rounded border p-3"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm">
          Contraseña
          <input
            className="rounded border p-3"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          className="student-primary rounded-lg p-3 disabled:opacity-50"
          disabled={pending || !ready}
          type="submit"
        >
          {pending ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </main>
  )
}
