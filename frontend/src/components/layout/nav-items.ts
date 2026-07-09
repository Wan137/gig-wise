import { LayoutDashboard, MessageCircle, Receipt } from 'lucide-react'

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/chat', label: 'Chat', icon: MessageCircle, end: false },
  { to: '/expenses', label: 'Expenses', icon: Receipt, end: false },
] as const
