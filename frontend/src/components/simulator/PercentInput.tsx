import type { ChangeEvent } from 'react'

interface PercentInputProps {
  name: string
  label: string
  value: number
  onChange: (name: string, value: number) => void
  required?: boolean
}

/** Percent input with a unit suffix and "예: 5% → 5 입력" help text, for any
 * remaining user-entered percent field. */
export default function PercentInput({
  name,
  label,
  value,
  onChange,
  required = true,
}: PercentInputProps) {
  return (
    <label className="text-sm font-semibold">
      {label}
      <div className="relative mt-2">
        <input
          name={name}
          type="number"
          min={0}
          max={100}
          step={0.01}
          required={required}
          value={value}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            onChange(name, Number(event.target.value))
          }
          className="w-full rounded-lg border border-gray-300 px-4 py-3 pr-9 font-normal"
        />
        <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">
          %
        </span>
      </div>
      <p className="mt-1 text-xs font-normal text-gray-400">예: 5% → 5 입력</p>
    </label>
  )
}
