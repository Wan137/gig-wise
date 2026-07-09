import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

type Tone = 'good' | 'warning' | 'critical' | 'neutral' | 'brand'

const TONE_CLASSES: Record<Tone, string> = {
  good: 'bg-status-good/10 text-status-good',
  warning: 'bg-status-warning/15 text-[#8a5a00] dark:text-status-warning',
  critical: 'bg-status-critical/10 text-status-critical',
  neutral: 'bg-surface-alt text-ink-secondary',
  brand: 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone
}

export function Badge({ className, tone = 'neutral', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium',
        TONE_CLASSES[tone],
        className,
      )}
      {...props}
    />
  )
}
