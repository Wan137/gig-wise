import type { ExpenseRecord } from '@/lib/api'
import { getCategoryMeta, formatCurrency } from '@/lib/categories'
import { Badge } from '@/components/ui/Badge'
import { Receipt } from 'lucide-react'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function ExpenseList({ expenses }: { expenses: ExpenseRecord[] }) {
  if (expenses.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-14 text-center text-ink-muted">
        <Receipt className="size-8" />
        <p className="text-sm">No receipts logged yet - upload one above to get started.</p>
      </div>
    )
  }

  return (
    <ul className="divide-y divide-border">
      {expenses.map((expense) => {
        const meta = getCategoryMeta(expense.category)
        const Icon = meta.icon
        return (
          <li key={expense.id} className="flex items-center gap-3 py-3.5">
            <div
              className="flex size-9 shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: `color-mix(in oklab, ${meta.colorVar} 16%, transparent)`, color: meta.colorVar }}
            >
              <Icon className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">{expense.vendor ?? 'Unknown vendor'}</p>
              <p className="text-xs text-ink-muted">
                {meta.label} · {formatDate(expense.created_at)}
              </p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <span className="text-sm font-semibold tabular-nums text-ink">
                {formatCurrency(expense.amount)}
              </span>
              <Badge tone={expense.tax_deductible ? 'good' : 'neutral'}>
                {expense.tax_deductible ? 'Deductible' : 'Not deductible'}
              </Badge>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
