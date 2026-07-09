import {
  Fuel,
  Wrench,
  Smartphone,
  ParkingCircle,
  ShieldCheck,
  Package,
  Ban,
  CircleDashed,
  type LucideIcon,
} from 'lucide-react'

export interface CategoryMeta {
  key: string
  label: string
  icon: LucideIcon
  /** Fixed categorical color slot (--color-cat-N) - order never changes,
   * per the dataviz skill's "assign categorical hues in fixed order" rule. */
  colorVar: string
}

// Order matches the backend's ExpenseCategory literal in
// backend/app/ocr/expense_classifier.py - keep both in sync.
export const CATEGORY_META: CategoryMeta[] = [
  { key: 'fuel', label: 'Fuel', icon: Fuel, colorVar: 'var(--color-cat-1)' },
  { key: 'vehicle_maintenance', label: 'Vehicle maintenance', icon: Wrench, colorVar: 'var(--color-cat-2)' },
  { key: 'phone_internet', label: 'Phone & internet', icon: Smartphone, colorVar: 'var(--color-cat-5)' },
  { key: 'tolls_parking', label: 'Tolls & parking', icon: ParkingCircle, colorVar: 'var(--color-cat-3)' },
  { key: 'vehicle_insurance', label: 'Vehicle insurance', icon: ShieldCheck, colorVar: 'var(--color-cat-7)' },
  { key: 'equipment_supplies', label: 'Equipment & supplies', icon: Package, colorVar: 'var(--color-cat-8)' },
  { key: 'personal_non_deductible', label: 'Personal (non-deductible)', icon: Ban, colorVar: 'var(--color-cat-6)' },
  { key: 'other', label: 'Other', icon: CircleDashed, colorVar: 'var(--color-cat-4)' },
]

const BY_KEY = new Map(CATEGORY_META.map((c) => [c.key, c]))

export function getCategoryMeta(key: string): CategoryMeta {
  return (
    BY_KEY.get(key) ?? {
      key,
      label: key.replace(/_/g, ' '),
      icon: CircleDashed,
      colorVar: 'var(--color-cat-4)',
    }
  )
}

export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '—'
  return `RM${amount.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
