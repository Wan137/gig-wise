import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Wallet, Receipt, PiggyBank, TrendingDown, MessageCircle, Upload } from 'lucide-react'
import { getExpenseSummary, getFinanceEstimate } from '@/lib/api'
import { formatCurrency } from '@/lib/categories'
import { StatTile } from '@/components/ui/StatTile'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { ExpenseCategoryChart } from '@/components/dashboard/ExpenseCategoryChart'
import { IncomeSetupCard } from '@/components/dashboard/IncomeSetupCard'

export function DashboardPage() {
  const summaryQuery = useQuery({ queryKey: ['expense-summary'], queryFn: getExpenseSummary })
  const estimateQuery = useQuery({ queryKey: ['finance-estimate'], queryFn: getFinanceEstimate })

  const loading = summaryQuery.isLoading || estimateQuery.isLoading

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Spinner className="size-6 text-brand-500" />
      </div>
    )
  }

  const summary = summaryQuery.data
  const estimate = estimateQuery.data

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Dashboard</h1>
        <p className="text-sm text-ink-muted">Your income, expenses, and estimated tax at a glance.</p>
      </div>

      {!estimate ? (
        <IncomeSetupCard />
      ) : (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Gross income"
            value={formatCurrency(estimate.gross_income)}
            icon={Wallet}
            tone="brand"
            hint={`YA${estimate.assessment_year}`}
          />
          <StatTile
            label="Estimated tax owed"
            value={formatCurrency(estimate.tax_owed)}
            icon={Receipt}
            tone="critical"
            hint={`${(estimate.effective_rate * 100).toFixed(2)}% effective rate`}
          />
          <StatTile
            label="Deductible expenses"
            value={formatCurrency(estimate.allowable_expenses)}
            icon={TrendingDown}
            tone="good"
          />
          <StatTile
            label="Suggested monthly set-aside"
            value={formatCurrency(estimate.monthly_set_aside)}
            icon={PiggyBank}
            tone="gold"
            hint="For your next tax payment"
          />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Expenses by category</CardTitle>
            {summary && summary.total_expenses > 0 && (
              <span className="text-sm font-medium text-ink-secondary tabular-nums">
                {formatCurrency(summary.total_expenses)} total
              </span>
            )}
          </CardHeader>
          <CardBody>
            {summary && summary.by_category.length > 0 ? (
              <ExpenseCategoryChart data={summary.by_category} />
            ) : (
              <div className="flex flex-col items-center gap-3 py-10 text-center">
                <div className="flex size-11 items-center justify-center rounded-full bg-surface-alt text-ink-muted">
                  <Receipt className="size-5" />
                </div>
                <p className="text-sm text-ink-muted">No expenses logged yet.</p>
                <Link
                  to="/expenses"
                  className="mt-1 inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-surface-alt px-3 text-sm font-medium text-ink-secondary transition-colors hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-brand-900/30"
                >
                  <Upload className="size-4" /> Log your first receipt
                </Link>
              </div>
            )}
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>EPF &amp; SOCSO</CardTitle>
          </CardHeader>
          <CardBody className="flex flex-col gap-4">
            {estimate ? (
              <>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                    {estimate.epf_scheme}
                  </p>
                  {estimate.epf_eligible ? (
                    <>
                      <p className="mt-1 text-xl font-semibold tabular-nums text-ink">
                        {formatCurrency(estimate.epf_suggested_monthly_contribution)}
                        <span className="text-sm font-normal text-ink-muted">/mo</span>
                      </p>
                      <p className="text-xs text-ink-muted">
                        Maximizes your {formatCurrency(estimate.epf_expected_annual_incentive)}/year
                        government incentive
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-ink-muted">Not eligible (60+)</p>
                  )}
                </div>
                <div className="h-px bg-border" />
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">SOCSO SKSPS</p>
                  <p className="mt-1 text-xl font-semibold tabular-nums text-ink">
                    {formatCurrency(estimate.socso_monthly_contribution)}
                    <span className="text-sm font-normal text-ink-muted">/mo</span>
                  </p>
                  <p className="text-xs text-ink-muted">
                    {formatCurrency(estimate.socso_annual_contribution)}/year
                  </p>
                </div>
              </>
            ) : (
              <p className="py-6 text-center text-sm text-ink-muted">
                Set your income to see suggested contributions.
              </p>
            )}
            <Link
              to="/chat"
              className="mt-1 flex items-center justify-center gap-1.5 rounded-lg border border-border py-2.5 text-sm font-medium text-ink-secondary transition-colors hover:bg-surface-alt hover:text-ink"
            >
              <MessageCircle className="size-4" /> Ask the copilot a question
            </Link>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
