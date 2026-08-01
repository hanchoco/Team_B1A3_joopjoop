import { CheckCircle2, Info } from 'lucide-react'
import type { ParsedPolicyContentItem } from '../../utils/policyContent'

interface PolicyContentListProps {
  items: ParsedPolicyContentItem[]
  emptyMessage?: string
  className?: string
}

export default function PolicyContentList({
  items,
  emptyMessage,
  className = 'mt-4',
}: PolicyContentListProps) {
  if (items.length === 0) {
    return emptyMessage ? (
      <p className={`${className} text-sm text-gray-500`}>{emptyMessage}</p>
    ) : null
  }

  return (
    <div className={`${className} space-y-3`}>
      {items.map((item, index) => {
        if (item.type === 'notice') {
          return (
            <div
              key={`${item.type}-${index}`}
              className="flex items-start gap-3 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-blue-950"
            >
              <Info size={17} className="mt-0.5 shrink-0 text-blue-600" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <span className="text-xs font-bold text-blue-700">안내</span>
                <p className="mt-1 break-words text-sm leading-6">{item.text}</p>
              </div>
            </div>
          )
        }

        if (item.type === 'primary') {
          return (
            <div
              key={`${item.type}-${index}`}
              className="flex items-start gap-3 text-sm leading-6 text-gray-600"
            >
              <CheckCircle2
                size={17}
                className="mt-0.5 shrink-0 text-blue-600"
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 break-words">{item.text}</span>
            </div>
          )
        }

        if (item.type === 'secondary') {
          return (
            <div
              key={`${item.type}-${index}`}
              className="flex items-start gap-2 pl-7 text-sm leading-6 text-gray-500"
            >
              <span
                aria-hidden="true"
                className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400"
              />
              <span className="min-w-0 flex-1 break-words">{item.text}</span>
            </div>
          )
        }

        if (item.type === 'process') {
          const processStepNumber = items
            .slice(0, index + 1)
            .filter((currentItem) => currentItem.type === 'process').length
          return (
            <div
              key={`${item.type}-${index}`}
              className="flex items-start gap-3 rounded-lg bg-slate-50 px-4 py-3"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-blue-600 text-xs font-bold text-white">
                {processStepNumber}
              </span>
              <p className="min-w-0 flex-1 break-words text-sm leading-6 text-gray-700">
                {item.text}
              </p>
            </div>
          )
        }

        return (
          <p
            key={`${item.type}-${index}`}
            className="max-w-3xl break-words text-sm leading-7 text-gray-600"
          >
            {item.text}
          </p>
        )
      })}
    </div>
  )
}
