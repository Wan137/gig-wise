import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Wallet } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { login, getMe, ApiError } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'

export function LoginPage() {
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const token = await login(email, password)
      useAuthStore.setState({ token })
      const user = await getMe()
      setSession(token, user)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-page px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-xl bg-brand-500 text-white shadow-sm">
            <Wallet className="size-6" strokeWidth={2.25} />
          </div>
          <div className="text-center">
            <h1 className="text-lg font-semibold text-ink">Welcome back</h1>
            <p className="text-sm text-ink-muted">Sign in to your Gig-Wise account</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-6 shadow-[var(--shadow-card)]">
          <Input
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="Password"
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-status-critical">{error}</p>}
          <Button type="submit" size="lg" loading={loading} className="mt-1 w-full">
            Sign in
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-ink-muted">
          Don't have an account?{' '}
          <Link to="/signup" className="font-medium text-brand-600 hover:underline dark:text-brand-300">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
