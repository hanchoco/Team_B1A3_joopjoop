import { LoaderCircle, SearchX } from 'lucide-react'

interface ContentStatePanelProps {
  variant: 'loading' | 'empty'
  title: string
  description: string
}

export default function ContentStatePanel({ variant, title, description }: ContentStatePanelProps) {
  const isLoading = variant === 'loading'

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy={isLoading}
      className="mt-6 flex min-h-64 items-center justify-center rounded-xl border border-gray-200 bg-white px-6 py-12 text-center"
    >
      <div className="flex max-w-sm flex-col items-center">
        <span
          className={`grid h-14 w-14 place-items-center rounded-full ${
            isLoading ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-gray-500'
          }`}
        >
          {isLoading ? (
            <LoaderCircle className="h-7 w-7 animate-spin" aria-hidden="true" />
          ) : (
            <SearchX className="h-7 w-7" aria-hidden="true" />
          )}
        </span>
        <strong className="mt-4 text-base font-bold text-gray-950">{title}</strong>
        <p className="mt-2 text-sm leading-6 text-gray-500">{description}</p>
      </div>
    </div>
  )
}
