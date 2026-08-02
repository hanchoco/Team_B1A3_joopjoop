import { Fragment } from 'react'

interface KnownRuleInfoProps {
  items: { label: string; value: string }[]
}

/** Read-only display of values the policy already knows
 * (calculation_rule_json) - never rendered as an editable input. */
export default function KnownRuleInfo({ items }: KnownRuleInfoProps) {
  if (items.length === 0) return null

  return (
    <div className="mb-5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-gray-500">
      {items.map((item, index) => (
        <Fragment key={item.label}>
          {index > 0 && <span className="text-gray-300">|</span>}
          <span>
            {item.label}: <span className="font-semibold text-gray-900">{item.value}</span>
          </span>
        </Fragment>
      ))}
    </div>
  )
}
