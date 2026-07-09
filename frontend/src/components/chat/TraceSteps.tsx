import { Compass, BookOpenText, Camera, Calculator, ShieldCheck, MessageCircle, Clock, CheckCircle2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { ThinkingDots } from '@/components/ui/Spinner'

const NODE_ICON: Record<string, LucideIcon> = {
  orchestrator: Compass,
  tax_advisor: BookOpenText,
  expense_tracker: Camera,
  financial_planner: Calculator,
  verifier: ShieldCheck,
  responder: MessageCircle,
  not_implemented: Clock,
}

export interface TraceEntry {
  node: string
  message: string
}

export function TraceSteps({ steps, isLive }: { steps: TraceEntry[]; isLive: boolean }) {
  if (steps.length === 0) return null

  return (
    <ol className="flex flex-col gap-2">
      {steps.map((step, i) => {
        const Icon = NODE_ICON[step.node] ?? Compass
        const isLast = i === steps.length - 1
        const isCurrent = isLive && isLast
        return (
          <li
            key={`${step.node}-${i}`}
            className="animate-trace-in flex items-center gap-2.5 text-sm"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <span
              className={
                isCurrent
                  ? 'flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300'
                  : 'flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-alt text-ink-muted'
              }
            >
              {isCurrent ? <Icon className="size-3.5" /> : <CheckCircle2 className="size-3.5" />}
            </span>
            <span className={isCurrent ? 'font-medium text-ink' : 'text-ink-muted line-through decoration-ink-muted/40'}>
              {step.message}
            </span>
            {isCurrent && <ThinkingDots className="text-brand-500" />}
          </li>
        )
      })}
    </ol>
  )
}
