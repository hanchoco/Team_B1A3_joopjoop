interface KnownRuleInfoProps {
  items: { label: string; value: string }[]
}

/** Read-only display of values the policy already knows
 * (calculation_rule_json) - never rendered as an editable input. */
export default function KnownRuleInfo({ items }: KnownRuleInfoProps) {
  if (items.length === 0) return null

  return (
    <div className="mb-5 grid gap-2 rounded-lg bg-slate-50 p-4 text-sm sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between gap-2">
          <span className="text-gray-500">{item.label}</span>
          <span className="font-semibold">{item.value}</span>
        </div>
      ))}
    </div>
  )
}
