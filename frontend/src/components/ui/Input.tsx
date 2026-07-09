import { type InputHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, label, error, id, ...props },
  ref,
) {
  const inputId = id ?? props.name
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-ink-secondary">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={cn(
          'h-11 rounded-lg border border-border bg-surface px-3.5 text-sm text-ink placeholder:text-ink-muted',
          'transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30',
          error && 'border-status-critical focus:border-status-critical focus:ring-status-critical/20',
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs text-status-critical">{error}</p>}
    </div>
  )
})
