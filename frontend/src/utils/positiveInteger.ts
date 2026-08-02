export const MIN_POSITIVE_INTEGER = 1

interface PositiveIntegerConstraints {
  max?: number
  min?: number
  unit?: string
}

export interface PositiveIntegerValidation {
  error: string
  value: number | undefined
}

export function sanitizeIntegerInput(value: string): string {
  return value.replace(/\D/g, '')
}

export function validatePositiveIntegerInput(
  value: string,
  { min = MIN_POSITIVE_INTEGER, max, unit = '' }: PositiveIntegerConstraints = {},
): PositiveIntegerValidation {
  if (value === '') return { error: '', value: undefined }

  if (!/^\d+$/.test(value)) {
    return { error: '양의 정수만 입력해 주세요.', value: undefined }
  }

  const numeric = Number(value)
  if (!Number.isSafeInteger(numeric)) {
    return { error: '올바른 정수를 입력해 주세요.', value: undefined }
  }
  if (numeric < min) {
    return { error: `${min}${unit} 이상 입력해 주세요.`, value: undefined }
  }
  if (max !== undefined && numeric > max) {
    return { error: `${max}${unit} 이하로 입력해 주세요.`, value: undefined }
  }

  return { error: '', value: numeric }
}
