import { type DragEvent, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Camera, Loader2, UploadCloud } from 'lucide-react'
import { cn } from '@/lib/cn'
import { uploadReceipt, ApiError } from '@/lib/api'

export function ReceiptUploadZone() {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: uploadReceipt,
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-summary'] })
      queryClient.invalidateQueries({ queryKey: ['finance-estimate'] })
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : 'Could not process that receipt.')
    },
  })

  function handleFiles(files: FileList | null) {
    const file = files?.[0]
    if (!file) return
    mutation.mutate(file)
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors',
          isDragging
            ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/20'
            : 'border-border bg-surface-alt hover:border-brand-300 hover:bg-brand-50/50 dark:hover:bg-brand-900/10',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {mutation.isPending ? (
          <>
            <Loader2 className="size-8 animate-spin text-brand-500" />
            <p className="text-sm font-medium text-ink">Reading your receipt...</p>
            <p className="text-xs text-ink-muted">Running OCR and categorizing the expense</p>
          </>
        ) : (
          <>
            <div className="flex size-12 items-center justify-center rounded-full bg-brand-100 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300">
              <UploadCloud className="size-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-ink">
                <span className="hidden sm:inline">Drag a receipt photo here, or </span>
                <span className="text-brand-600 dark:text-brand-300">browse to upload</span>
              </p>
              <p className="mt-1 flex items-center justify-center gap-1 text-xs text-ink-muted">
                <Camera className="size-3.5" /> JPEG, PNG, or WebP - up to 10MB
              </p>
            </div>
          </>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-status-critical">{error}</p>}
      {mutation.isSuccess && !mutation.isPending && (
        <p className="mt-2 text-sm text-status-good">
          Logged {mutation.data.vendor ?? 'expense'} as {mutation.data.category.replace(/_/g, ' ')}.
        </p>
      )}
    </div>
  )
}
