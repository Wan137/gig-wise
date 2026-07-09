import { LogOut, Wallet } from 'lucide-react'
import { useAuthStore } from '@/lib/auth-store'
import { ThemeToggle } from './ThemeToggle'

export function MobileTopBar() {
  const logout = useAuthStore((s) => s.logout)

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4 md:hidden">
      <div className="flex items-center gap-2">
        <div className="flex size-7 items-center justify-center rounded-md bg-brand-500 text-white">
          <Wallet className="size-4" strokeWidth={2.25} />
        </div>
        <span className="text-sm font-semibold text-ink">Gig-Wise</span>
      </div>
      <div className="flex items-center gap-1">
        <ThemeToggle />
        <button
          type="button"
          onClick={logout}
          aria-label="Log out"
          className="flex size-9 items-center justify-center rounded-lg text-ink-secondary hover:bg-surface-alt hover:text-status-critical"
        >
          <LogOut className="size-[18px]" strokeWidth={2} />
        </button>
      </div>
    </header>
  )
}
