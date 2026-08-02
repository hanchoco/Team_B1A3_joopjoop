import { ExternalLink } from 'lucide-react'

interface OnlineApplicationLinkProps {
  url: string | null | undefined
  className?: string
  variant?: 'text' | 'button'
}

const VARIANT_CLASSES: Record<NonNullable<OnlineApplicationLinkProps['variant']>, string> = {
  text: 'gap-1 text-xs font-semibold text-blue-600 hover:underline focus-visible:rounded-sm',
  button:
    'gap-2 rounded-lg border border-blue-600 bg-white px-4 py-3 text-sm font-bold text-blue-600 transition-colors hover:bg-blue-50',
}

export default function OnlineApplicationLink({
  url,
  className = '',
  variant = 'text',
}: OnlineApplicationLinkProps) {
  const href = url?.trim()

  if (!href) return null

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label="온라인 신청 페이지 바로가기(새 탭에서 열림)"
      className={`inline-flex cursor-pointer items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 ${VARIANT_CLASSES[variant]} ${className}`}
    >
      <span>온라인 신청 페이지 바로가기</span>
      <ExternalLink size={14} className="shrink-0" aria-hidden="true" />
    </a>
  )
}
