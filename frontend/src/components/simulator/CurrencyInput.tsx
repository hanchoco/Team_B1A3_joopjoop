import type { ChangeEvent } from 'react'

interface CurrencyInputProps {
  name: string
  label: string
  value: number | undefined
  onChange: (name: string, value: number | undefined) => void
  required?: boolean
  placeholder?: string
  /** Extra note shown below the Korean amount helper text, e.g. "계산에 포함되지 않아요". */
  note?: string
}

function formatAmountInput(value: number | undefined): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.trunc(value).toLocaleString('ko-KR')
    : ''
}

function formatKoreanWon(value: number | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return ''

  const amount = Math.max(0, Math.trunc(value))
  if (amount === 0) return '0원'

  const eok = Math.floor(amount / 100_000_000)
  const man = Math.floor((amount % 100_000_000) / 10_000)
  const won = amount % 10_000
  const parts: string[] = []

  if (eok > 0) parts.push(`${eok.toLocaleString('ko-KR')}억`)
  if (man > 0) parts.push(`${man.toLocaleString('ko-KR')}만`)
  if (won > 0) parts.push(`${won.toLocaleString('ko-KR')}원`)
  else parts.push('원')

  return parts.join(' ')
}

/** Amount input matching the onboarding/추가질문 currency UX: comma-formatted digits
 * on input, with a real-time Korean-unit helper text below. */
export default function CurrencyInput({
  name,
  label,
  value,
  onChange,
  required = false,
  placeholder = '0',
  note,
}: CurrencyInputProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const digits = event.target.value.replace(/\D/g, '')
    onChange(name, digits === '' ? undefined : Number(digits))
  }

  return (
    <label className="text-sm font-semibold">
      {label}
      <div className="relative mt-2">
        <input
          name={name}
          type="text"
          inputMode="numeric"
          required={required}
          value={formatAmountInput(value)}
          onChange={handleChange}
          placeholder={placeholder}
          className="w-full rounded-lg border border-gray-300 px-4 py-3 pr-10 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
        <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">
          원
        </span>
      </div>
      {typeof value === 'number' && (
        <p className="mt-1 px-1 text-xs font-normal text-gray-400" aria-live="polite">
          {formatKoreanWon(value)}
        </p>
      )}
      {note && <p className="mt-1 px-1 text-xs font-normal text-gray-400">{note}</p>}
    </label>
  )
}
