import { Wallet } from 'lucide-react'
import { cn } from '@/lib/cn'
import { MarkdownMessage } from './MarkdownMessage'

export interface DisplayMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function MessageBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('animate-message-in flex gap-2.5', isUser && 'flex-row-reverse')}>
      {!isUser && (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white">
          <Wallet className="size-3.5" strokeWidth={2.25} />
        </div>
      )}
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3 sm:max-w-[75%]',
          isUser
            ? 'rounded-tr-sm bg-brand-500 text-white'
            : 'rounded-tl-sm border border-border bg-surface text-ink shadow-[var(--shadow-card)]',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</p>
        ) : (
          <MarkdownMessage content={message.content} />
        )}
      </div>
    </div>
  )
}
