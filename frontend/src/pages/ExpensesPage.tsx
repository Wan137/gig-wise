import { useQuery } from '@tanstack/react-query'
import { listExpenses } from '@/lib/api'
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { ReceiptUploadZone } from '@/components/expenses/ReceiptUploadZone'
import { ExpenseList } from '@/components/expenses/ExpenseList'

export function ExpensesPage() {
  const { data, isLoading } = useQuery({ queryKey: ['expenses'], queryFn: listExpenses })

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Expenses</h1>
        <p className="text-sm text-ink-muted">
          Upload a receipt photo and we'll read, categorize, and flag it as tax-deductible or not.
        </p>
      </div>

      <div className="mb-6">
        <ReceiptUploadZone />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Logged receipts</CardTitle>
        </CardHeader>
        <CardBody className="pt-0">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Spinner className="size-5 text-brand-500" />
            </div>
          ) : (
            <ExpenseList expenses={data ?? []} />
          )}
        </CardBody>
      </Card>
    </div>
  )
}
