import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { CategoryTotal } from '@/lib/api'
import { getCategoryMeta, formatCurrency } from '@/lib/categories'

interface Props {
  data: CategoryTotal[]
}

interface TooltipPayloadEntry {
  payload: { key: string; label: string; amount: number; count: number }
}

function ChartTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadEntry[] }) {
  if (!active || !payload?.length) return null
  const { label, amount, count } = payload[0].payload
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-sm shadow-[var(--shadow-elevated)]">
      <p className="font-medium text-ink">{label}</p>
      <p className="tabular-nums text-ink-secondary">
        {formatCurrency(amount)} · {count} {count === 1 ? 'receipt' : 'receipts'}
      </p>
    </div>
  )
}

export function ExpenseCategoryChart({ data }: Props) {
  const rows = data
    .map((row) => {
      const meta = getCategoryMeta(row.category)
      return { key: row.category, label: meta.label, amount: row.total_amount, count: row.count, color: meta.colorVar }
    })
    .sort((a, b) => b.amount - a.amount)

  const height = Math.max(rows.length * 40 + 16, 120)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }} barCategoryGap={10}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="label"
          width={148}
          tickLine={false}
          axisLine={false}
          tick={{ fill: 'var(--color-ink-secondary)', fontSize: 12.5 }}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--color-surface-alt)' }} />
        <Bar dataKey="amount" radius={[0, 6, 6, 0]} maxBarSize={20}>
          {rows.map((row) => (
            <Cell key={row.key} fill={row.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
