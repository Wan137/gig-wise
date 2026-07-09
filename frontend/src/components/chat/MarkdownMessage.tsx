import ReactMarkdown from 'react-markdown'

export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="prose-chat text-[15px] leading-relaxed">
      <ReactMarkdown
        components={{
          p: ({ ...props }) => <p className="mb-2.5 last:mb-0" {...props} />,
          ul: ({ ...props }) => <ul className="mb-2.5 list-disc space-y-1 pl-5 last:mb-0" {...props} />,
          ol: ({ ...props }) => <ol className="mb-2.5 list-decimal space-y-1 pl-5 last:mb-0" {...props} />,
          strong: ({ ...props }) => <strong className="font-semibold" {...props} />,
          a: ({ ...props }) => (
            <a className="text-brand-600 underline underline-offset-2 dark:text-brand-300" target="_blank" rel="noreferrer" {...props} />
          ),
          hr: ({ ...props }) => <hr className="my-3 border-border" {...props} />,
          h1: ({ ...props }) => <p className="mb-1 font-semibold" {...props} />,
          h2: ({ ...props }) => <p className="mb-1 font-semibold" {...props} />,
          h3: ({ ...props }) => <p className="mb-1 font-semibold" {...props} />,
          code: ({ ...props }) => (
            <code className="rounded bg-surface-alt px-1 py-0.5 font-mono text-[13px]" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
