import { useAuthStore } from './auth-store'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.errors) && body.errors.length > 0) {
      return body.errors.map((e: { msg?: string }) => e.msg).filter(Boolean).join(' ')
    }
  } catch {
    // response wasn't JSON - fall through to the generic message below
  }
  return `Request failed (${response.status}).`
}

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  })
  if (response.status === 401) {
    useAuthStore.getState().logout()
  }
  if (!response.ok) {
    throw new ApiError(response.status, await extractErrorMessage(response))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

// --- Auth ---------------------------------------------------------------

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  created_at: string
}

export function signup(email: string, password: string, fullName: string) {
  return request<AuthUser>('/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName || undefined }),
  })
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password })
  const data = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  return data.access_token
}

export function getMe() {
  return request<AuthUser>('/auth/me')
}

// --- Chat -----------------------------------------------------------------

export interface ChatSession {
  id: string
  title: string
  created_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export function createChatSession() {
  return request<ChatSession>('/chat/sessions', { method: 'POST' })
}

export function listChatSessions() {
  return request<ChatSession[]>('/chat/sessions')
}

export function getChatMessages(sessionId: string) {
  return request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`)
}

export interface StreamHandlers {
  onTrace: (node: string, message: string) => void
  onFinal: (answer: string) => void
  onError: (message: string) => void
}

/** Parses "event: X\ndata: Y\n\n" blocks off a fetch() streaming body.
 *
 * A plain EventSource can't be used here - it only supports GET requests
 * with no custom headers, and this endpoint needs a POST body plus a Bearer
 * auth header - so the SSE framing is parsed by hand from the fetch stream.
 */
export async function streamChatMessage(sessionId: string, content: string, handlers: StreamHandlers) {
  const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ content }),
  })

  if (!response.ok || !response.body) {
    handlers.onError(await extractErrorMessage(response))
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    // sse-starlette writes CRLF line endings ("\r\n\r\n" between frames), per
    // the SSE spec's allowance for either terminator - normalize to "\n" so
    // the rest of this parser can assume a single line-ending style.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      let eventType = 'message'
      let data = ''
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event:')) eventType = line.slice(6).trim()
        else if (line.startsWith('data:')) data += line.slice(5).trim()
      }

      if (data) {
        try {
          const parsed = JSON.parse(data)
          if (eventType === 'trace') handlers.onTrace(parsed.node, parsed.message)
          else if (eventType === 'final') handlers.onFinal(parsed.answer)
          else if (eventType === 'error') handlers.onError(parsed.message)
        } catch {
          // Malformed event frame - skip it rather than crashing the stream.
        }
      }

      boundary = buffer.indexOf('\n\n')
    }
  }
}

// --- Expenses ---------------------------------------------------------------

export interface ExpenseRecord {
  id: string
  vendor: string | null
  amount: number | null
  expense_date: string | null
  category: string
  tax_deductible: boolean
  ocr_confidence: number | null
  created_at: string
}

export interface CategoryTotal {
  category: string
  total_amount: number
  count: number
  tax_deductible: boolean
}

export interface ExpenseSummary {
  total_expenses: number
  total_deductible: number
  by_category: CategoryTotal[]
}

export async function uploadReceipt(file: File) {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${API_BASE_URL}/expenses/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  if (!response.ok) throw new ApiError(response.status, await extractErrorMessage(response))
  return response.json() as Promise<ExpenseRecord>
}

export function listExpenses() {
  return request<ExpenseRecord[]>('/expenses')
}

export function getExpenseSummary() {
  return request<ExpenseSummary>('/expenses/summary')
}

// --- Profile ---------------------------------------------------------------

export interface TaxProfile {
  date_of_birth: string | null
  occupation_sector: string | null
  is_epf_member: boolean
  estimated_annual_income: number | null
}

export function getTaxProfile() {
  return request<TaxProfile>('/profile/tax-profile')
}

export function updateTaxProfile(update: Partial<TaxProfile>) {
  return request<TaxProfile>('/profile/tax-profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
}

// --- Finance (deterministic, no LLM) ---------------------------------------

export interface FinanceEstimate {
  assessment_year: number
  gross_income: number
  allowable_expenses: number
  chargeable_income: number
  tax_owed: number
  effective_rate: number
  monthly_set_aside: number
  cp500_instalment_amount: number
  epf_scheme: string
  epf_eligible: boolean
  epf_suggested_monthly_contribution: number
  epf_expected_annual_incentive: number
  socso_monthly_contribution: number
  socso_annual_contribution: number
}

/** Returns null (rather than throwing) when the user hasn't set an income
 * estimate yet - the dashboard treats that as "show the setup prompt", not
 * an error state. */
export async function getFinanceEstimate(): Promise<FinanceEstimate | null> {
  try {
    return await request<FinanceEstimate>('/finance/estimate')
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
