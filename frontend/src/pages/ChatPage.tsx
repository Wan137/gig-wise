import { useEffect, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import {
  createChatSession,
  getChatMessages,
  listChatSessions,
  streamChatMessage,
  type ChatMessage,
} from '@/lib/api'
import { Spinner } from '@/components/ui/Spinner'
import { MessageBubble, type DisplayMessage } from '@/components/chat/MessageBubble'
import { TraceSteps, type TraceEntry } from '@/components/chat/TraceSteps'
import { ChatInput } from '@/components/chat/ChatInput'

function toDisplayMessage(m: ChatMessage): DisplayMessage {
  return { id: m.id, role: m.role, content: m.content }
}

export function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [liveTrace, setLiveTrace] = useState<TraceEntry[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [initializing, setInitializing] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        const sessions = await listChatSessions()
        const session = sessions[0] ?? (await createChatSession())
        if (cancelled) return
        setSessionId(session.id)
        const history = await getChatMessages(session.id)
        if (cancelled) return
        setMessages(history.map(toDisplayMessage))
      } catch {
        if (!cancelled) setError('Could not load your conversation. Please refresh the page.')
      } finally {
        if (!cancelled) setInitializing(false)
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, liveTrace])

  async function handleSend(content: string) {
    if (!sessionId) return
    setError(null)
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: 'user', content }])
    setLiveTrace([])
    setIsStreaming(true)

    await streamChatMessage(sessionId, content, {
      onTrace: (node, message) => setLiveTrace((prev) => [...prev, { node, message }]),
      onFinal: (answer) => {
        setMessages((prev) => [...prev, { id: `local-${Date.now()}-a`, role: 'assistant', content: answer }])
        setLiveTrace([])
        setIsStreaming(false)
      },
      onError: (message) => {
        setError(message)
        setLiveTrace([])
        setIsStreaming(false)
      },
    })
  }

  if (initializing) {
    return (
      <div className="flex h-full min-h-[70vh] items-center justify-center">
        <Spinner className="size-6 text-brand-500" />
      </div>
    )
  }

  const isEmpty = messages.length === 0

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col px-4 py-4 sm:px-6 md:h-screen md:py-6">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto pb-2">
        {isEmpty && !isStreaming && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-ink-muted">
            <p className="text-base font-medium text-ink">What can I help you with?</p>
            <p className="max-w-sm text-sm">
              Ask about LHDN tax rules, EPF/SOCSO contributions, or how much you should set aside this
              month.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isStreaming && (
          <div className="flex gap-2.5">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white opacity-80">
              <Spinner className="size-3.5" />
            </div>
            <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
              {liveTrace.length > 0 ? (
                <TraceSteps steps={liveTrace} isLive />
              ) : (
                <p className="text-sm text-ink-muted">Understanding your question...</p>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-status-critical/20 bg-status-critical/5 px-4 py-3 text-sm text-status-critical">
            <AlertTriangle className="size-4 shrink-0" />
            {error}
          </div>
        )}
      </div>

      <div className="pt-3">
        <ChatInput onSend={handleSend} disabled={isStreaming || !sessionId} />
      </div>
    </div>
  )
}
