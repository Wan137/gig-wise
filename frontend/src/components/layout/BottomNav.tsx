import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { NAV_ITEMS } from './nav-items'

export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-surface/95 backdrop-blur-sm md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex flex-1 flex-col items-center gap-1 py-2.5 text-xs font-medium transition-colors',
              isActive ? 'text-brand-600 dark:text-brand-300' : 'text-ink-muted',
            )
          }
        >
          <Icon className="size-5" strokeWidth={2} />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
