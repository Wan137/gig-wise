import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { applyTheme, getInitialTheme, type Theme } from '@/lib/theme'
import { cn } from '@/lib/cn'

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <button
      type="button"
      onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
      aria-label="Toggle color theme"
      className={cn(
        'relative flex size-9 items-center justify-center rounded-lg text-ink-secondary transition-colors hover:bg-surface-alt hover:text-ink',
        className,
      )}
    >
      <Sun className="size-[18px] scale-100 dark:scale-0 transition-transform" />
      <Moon className="absolute size-[18px] scale-0 dark:scale-100 transition-transform" />
    </button>
  )
}
