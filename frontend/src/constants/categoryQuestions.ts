export const EMPLOYMENT_COMPANY_SIZE_QUESTION_KEY = 'employment.company_size_code'
export const LEGACY_EMPLOYMENT_COMPANY_SIZE_QUESTION_KEY = 'employment.company_size'

export const COMPANY_SIZE_OPTION_LABELS: Record<string, string> = {
  MICRO: '5인 미만',
  SMALL: '5인 이상 50인 미만',
  MEDIUM: '50인 이상 300인 미만',
  LARGE: '300인 이상',
  PUBLIC: '공공기관·공기업',
  UNKNOWN: '현재 근무 중이 아님',
}

export function getCompanySizeOptionLabel(value: string, fallbackLabel: string): string {
  return COMPANY_SIZE_OPTION_LABELS[value] ?? fallbackLabel
}
