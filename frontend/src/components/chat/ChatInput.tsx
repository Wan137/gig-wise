import { type KeyboardEvent, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/cn'

interface Props {
  onSend: (content: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  function handleSend() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    requestAnimationFrame(autoResize)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 shadow-[var(--shadow-card)]">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        placeholder="Ask about taxes, EPF, SOCSO, or your expenses..."
        onChange={(e) => {
          setValue(e.target.value)
          autoResize()
        }}
        onKeyDown={handleKeyDown}
        className="max-h-40 flex-1 resize-none bg-transparent px-2.5 py-2 text-[15px] text-ink placeholder:text-ink-muted focus:outline-none"
      />
      <button
        type="button"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-xl transition-all',
          disabled || !value.trim()
            ? 'bg-surface-alt text-ink-muted'
            : 'bg-brand-500 text-white hover:bg-brand-600 active:scale-95',
        )}
      >
        <Send className="size-4" strokeWidth={2.25} />
      </button>
    </div>
  )
}
