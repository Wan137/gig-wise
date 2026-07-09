import { NavLink } from 'react-router-dom'
import { LogOut, Wallet } from 'lucide-react'
import { cn } from '@/lib/cn'
import { useAuthStore } from '@/lib/auth-store'
import { NAV_ITEMS } from './nav-items'
import { ThemeToggle } from './ThemeToggle'

export function Sidebar() {
  const { user, logout } = useAuthStore()

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex h-16 items-center gap-2.5 px-6">
        <div className="flex size-8 items-center justify-center rounded-lg bg-brand-500 text-white">
          <Wallet className="size-[18px]" strokeWidth={2.25} />
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-ink">Gig-Wise</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200'
                  : 'text-ink-secondary hover:bg-surface-alt hover:text-ink',
              )
            }
          >
            <Icon className="size-[18px]" strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="flex items-center gap-2 border-t border-border px-3 py-3">
        <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-2 py-1.5">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gold-100 text-sm font-semibold text-gold-700 dark:bg-gold-900/50 dark:text-gold-200">
            {(user?.full_name ?? user?.email ?? '?').charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{user?.full_name || 'Your account'}</p>
            <p className="truncate text-xs text-ink-muted">{user?.email}</p>
          </div>
        </div>
        <ThemeToggle />
        <button
          type="button"
          onClick={logout}
          aria-label="Log out"
          className="flex size-9 items-center justify-center rounded-lg text-ink-secondary transition-colors hover:bg-surface-alt hover:text-status-critical"
        >
          <LogOut className="size-[18px]" strokeWidth={2} />
        </button>
      </div>
    </aside>
  )
}
