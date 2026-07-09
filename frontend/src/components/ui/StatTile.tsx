import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Card } from './Card'

interface StatTileProps {
  label: string
  value: string
  icon: LucideIcon
  tone?: 'brand' | 'gold' | 'good' | 'critical'
  hint?: string
}

const TONE_CLASSES: Record<NonNullable<StatTileProps['tone']>, string> = {
  brand: 'bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300',
  gold: 'bg-gold-50 text-gold-600 dark:bg-gold-900/40 dark:text-gold-300',
  good: 'bg-status-good/10 text-status-good',
  critical: 'bg-status-critical/10 text-status-critical',
}

export function StatTile({ label, value, icon: Icon, tone = 'brand', hint }: StatTileProps) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium leading-snug text-ink-secondary">{label}</p>
          <p className="mt-1.5 truncate text-xl font-semibold tracking-tight tabular-nums text-ink sm:text-2xl">
            {value}
          </p>
          {hint && <p className="mt-1 truncate text-xs text-ink-muted">{hint}</p>}
        </div>
        <div className={cn('flex size-9 shrink-0 items-center justify-center rounded-xl', TONE_CLASSES[tone])}>
          <Icon className="size-[18px]" strokeWidth={2} />
        </div>
      </div>
    </Card>
  )
}
