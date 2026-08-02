import { useId, useState } from 'react'
import type { ChangeEvent, FocusEvent, KeyboardEvent } from 'react'
import {
  MIN_POSITIVE_INTEGER,
  sanitizeIntegerInput,
  validatePositiveIntegerInput,
} from '../../utils/positiveInteger'

interface PositiveIntegerInputProps {
  name: string
  label: string
  value: number | undefined
  onChange: (name: string, value: number | undefined) => void
  initialValue?: number
  max?: number
  min?: number
  unit?: string
  /** Extra note shown below the input, e.g. default-value guidance. */
  note?: string
}

function initialInputValue(value: number | undefined, initialValue: number | undefined): string {
  const numeric = value ?? initialValue
  return typeof numeric === 'number' && Number.isSafeInteger(numeric) ? String(numeric) : ''
}

export default function PositiveIntegerInput({
  name,
  label,
  value,
  onChange,
  initialValue,
  max,
  min = MIN_POSITIVE_INTEGER,
  unit = '개월',
  note,
}: PositiveIntegerInputProps) {
  const [inputValue, setInputValue] = useState(() => initialInputValue(value, initialValue ?? min))
  const [touched, setTouched] = useState(false)
  const errorId = useId()
  const validation = validatePositiveIntegerInput(inputValue, { min, max, unit })
  const showError = touched && validation.error !== ''

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const digits = sanitizeIntegerInput(event.target.value)
    const nextValidation = validatePositiveIntegerInput(digits, { min, max, unit })
    event.target.setCustomValidity(nextValidation.error)
    setInputValue(digits)
    onChange(name, nextValidation.value)
  }

  function handleBlur(event: FocusEvent<HTMLInputElement>) {
    event.target.setCustomValidity(validation.error)
    setTouched(true)
    if (validation.value !== undefined) setInputValue(String(validation.value))
  }

  function blockNonDigitKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.ctrlKey || event.metaKey || event.altKey) return
    if (event.key.length === 1 && !/^\d$/.test(event.key)) event.preventDefault()
  }

  return (
    <label className="text-sm font-semibold">
      {label}
      <div className="relative mt-2">
        <input
          name={name}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          min={min}
          max={max}
          value={inputValue}
          onChange={handleChange}
          onBlur={handleBlur}
          onKeyDown={blockNonDigitKey}
          onInvalid={() => setTouched(true)}
          aria-invalid={showError}
          aria-describedby={showError ? errorId : undefined}
          className={`w-full rounded-lg border px-4 py-3 pr-14 font-normal outline-none focus:ring-2 ${
            showError
              ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-100'
              : 'border-gray-300 focus:border-blue-500 focus:ring-blue-100'
          }`}
        />
        <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">
          {unit}
        </span>
      </div>
      {showError && (
        <p id={errorId} className="mt-1 px-1 text-xs font-normal text-rose-600" aria-live="polite">
          {validation.error}
        </p>
      )}
      {note && <p className="mt-1 px-1 text-xs font-normal text-gray-400">{note}</p>}
    </label>
  )
}
