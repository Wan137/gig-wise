import { type FormEvent, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { updateTaxProfile } from '@/lib/api'

const SECTORS = [
  { value: 'e_hailing', label: 'E-hailing driver' },
  { value: 'delivery_rider', label: 'Delivery / p-hailing rider' },
  { value: 'freelancer', label: 'Freelancer' },
  { value: 'other', label: 'Other' },
]

export function IncomeSetupCard() {
  const queryClient = useQueryClient()
  const [income, setIncome] = useState('')
  const [sector, setSector] = useState('e_hailing')

  const mutation = useMutation({
    mutationFn: () =>
      updateTaxProfile({ estimated_annual_income: Number(income), occupation_sector: sector }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-estimate'] })
      queryClient.invalidateQueries({ queryKey: ['tax-profile'] })
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!income || Number(income) <= 0) return
    mutation.mutate()
  }

  return (
    <Card>
      <CardBody className="flex flex-col items-center gap-4 py-10 text-center">
        <div className="flex size-12 items-center justify-center rounded-full bg-gold-50 text-gold-600 dark:bg-gold-900/40 dark:text-gold-300">
          <Sparkles className="size-6" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-ink">Get your tax estimate</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-ink-muted">
            Tell us roughly what you earn a year and we'll show your estimated tax, EPF, and SOCSO
            numbers instantly - computed by the same calculator the chat uses.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-3">
          <div className="flex flex-col gap-3 sm:flex-row">
            <Input
              type="number"
              min="0"
              step="100"
              placeholder="Annual income (RM)"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              className="flex-1"
            />
            <select
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="h-11 rounded-lg border border-border bg-surface px-3 text-sm text-ink focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30"
            >
              {SECTORS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <Button type="submit" loading={mutation.isPending} disabled={!income} className="w-full">
            Calculate my estimate
          </Button>
        </form>
      </CardBody>
    </Card>
  )
}
