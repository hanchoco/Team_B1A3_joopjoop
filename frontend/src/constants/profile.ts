import type {
  EmploymentStatusCode,
  HouseholdTypeCode,
  HousingTypeCode,
  IncomeBandCode,
} from '../types/api'

export const REGION_OPTIONS: { code: string | null; name: string }[] = [
  { code: '11', name: '서울' },
  { code: '41', name: '경기' },
  { code: '28', name: '인천' },
  { code: '26', name: '부산' },
  { code: '27', name: '대구' },
  { code: '29', name: '광주' },
  { code: '30', name: '대전' },
  { code: null, name: '그 외 지역' },
]

export const INCOME_BAND_OPTIONS: { code: IncomeBandCode; label: string }[] = [
  { code: 'BELOW_50', label: '중위소득 50% 미만' },
  { code: 'BETWEEN_50_75', label: '중위소득 50~75%' },
  { code: 'BETWEEN_75_100', label: '중위소득 75~100%' },
  { code: 'BETWEEN_100_120', label: '중위소득 100~120%' },
  { code: 'BETWEEN_120_150', label: '중위소득 120~150%' },
  { code: 'ABOVE_150', label: '중위소득 150% 초과' },
  { code: 'UNKNOWN', label: '잘 모름' },
]

export const EMPLOYMENT_STATUS_OPTIONS: { code: EmploymentStatusCode; label: string }[] = [
  { code: 'EMPLOYED', label: '재직 중' },
  { code: 'SELF_EMPLOYED', label: '프리랜서·자영업' },
  { code: 'JOB_SEEKER', label: '구직 중' },
  { code: 'UNEMPLOYED', label: '미취업' },
  { code: 'STUDENT', label: '학생' },
  { code: 'ON_LEAVE', label: '휴직 중' },
  { code: 'OTHER', label: '기타' },
]

export const HOUSEHOLD_TYPE_OPTIONS: { code: HouseholdTypeCode; label: string }[] = [
  { code: 'SINGLE', label: '1인 가구' },
  { code: 'COUPLE', label: '부부 가구' },
  { code: 'WITH_PARENTS', label: '부모와 거주' },
  { code: 'SINGLE_PARENT', label: '한부모 가구' },
  { code: 'MULTI_PERSON', label: '다인 가구' },
  { code: 'OTHER', label: '기타' },
]

export const HOUSING_TYPE_OPTIONS: { code: HousingTypeCode; label: string }[] = [
  { code: 'MONTHLY_RENT', label: '월세' },
  { code: 'JEONSE', label: '전세' },
  { code: 'OWNED', label: '자가' },
  { code: 'PUBLIC_RENTAL', label: '공공임대' },
  { code: 'DORMITORY', label: '기숙사·시설' },
  { code: 'WITH_FAMILY', label: '가족과 함께 거주' },
  { code: 'OTHER', label: '기타' },
]

export function regionNameByCode(code: string | null | undefined): string {
  return REGION_OPTIONS.find((option) => option.code === code)?.name ?? '미입력'
}

export function incomeBandLabel(code: IncomeBandCode | null | undefined): string {
  return INCOME_BAND_OPTIONS.find((option) => option.code === code)?.label ?? '미입력'
}

export function employmentStatusLabel(code: EmploymentStatusCode | null | undefined): string {
  return EMPLOYMENT_STATUS_OPTIONS.find((option) => option.code === code)?.label ?? '미입력'
}

export function householdTypeLabel(code: HouseholdTypeCode | null | undefined): string {
  return HOUSEHOLD_TYPE_OPTIONS.find((option) => option.code === code)?.label ?? '미입력'
}

export function housingTypeLabel(code: HousingTypeCode | null | undefined): string {
  return HOUSING_TYPE_OPTIONS.find((option) => option.code === code)?.label ?? '미입력'
}
