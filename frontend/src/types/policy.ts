export type EligibilityStatus = 'ELIGIBLE' | 'NEEDS_REVIEW' | 'INELIGIBLE'

export type BackendEligibilityStatus = '가능성 높음' | '추가 확인 필요' | '불충족'

export const eligibilityStatusLabels: Record<EligibilityStatus, BackendEligibilityStatus> = {
  ELIGIBLE: '가능성 높음',
  NEEDS_REVIEW: '추가 확인 필요',
  INELIGIBLE: '불충족',
}

const eligibilityStatusByLabel: Record<BackendEligibilityStatus, EligibilityStatus> = {
  '가능성 높음': 'ELIGIBLE',
  '추가 확인 필요': 'NEEDS_REVIEW',
  불충족: 'INELIGIBLE',
}

export function toEligibilityStatus(
  status: EligibilityStatus | BackendEligibilityStatus | null,
): EligibilityStatus | null {
  if (status === null) return null
  return status in eligibilityStatusByLabel
    ? eligibilityStatusByLabel[status as BackendEligibilityStatus]
    : (status as EligibilityStatus)
}
