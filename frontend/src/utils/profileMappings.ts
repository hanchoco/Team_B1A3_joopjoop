import type { UserProfile, UserProfileUpdate } from '../types'
import type {
  EmploymentStatusCode,
  HouseholdTypeCode,
  HousingTypeCode,
  IncomeBandCode,
  UserProfilePatch,
  UserProfileResponse,
} from '../api/users'

const employmentToCode: Record<string, EmploymentStatusCode> = {
  '재직 중': 'EMPLOYED',
  '프리랜서·자영업': 'SELF_EMPLOYED',
  미취업: 'UNEMPLOYED',
  '구직 중': 'JOB_SEEKER',
  학생: 'STUDENT',
  휴직: 'ON_LEAVE',
  '휴직 중': 'ON_LEAVE',
  기타: 'OTHER',
}

const householdToCode: Record<string, HouseholdTypeCode> = {
  '1인 가구': 'SINGLE',
  '부부 가구': 'COUPLE',
  '부모와 거주': 'WITH_PARENTS',
  '한부모 가구': 'SINGLE_PARENT',
  '자녀가 있는 가구': 'MULTI_PERSON',
  기타: 'OTHER',
}

const housingToCode: Record<string, HousingTypeCode> = {
  자가: 'OWNED',
  전세: 'JEONSE',
  월세: 'MONTHLY_RENT',
  공공임대: 'PUBLIC_RENTAL',
  '기숙사·시설': 'DORMITORY',
  '가족과 함께 거주': 'WITH_FAMILY',
  기타: 'OTHER',
}

const incomeToCode: Record<string, IncomeBandCode> = {
  '월 100만 원 이하': 'BELOW_50',
  '월 101~200만 원': 'BETWEEN_50_75',
  '월 201~300만 원': 'BETWEEN_75_100',
  '중위소득 100~120%': 'BETWEEN_100_120',
  '중위소득 120~150%': 'BETWEEN_120_150',
  '월 301만 원 이상': 'ABOVE_150',
  '소득 미확인': 'UNKNOWN',
}

function reverseMap<T extends string>(mapping: Record<string, T>): Record<T, string> {
  return Object.fromEntries(
    Object.entries(mapping).map(([label, code]) => [code, label]),
  ) as Record<T, string>
}

const employmentFromCode = reverseMap(employmentToCode)
const householdFromCode = reverseMap(householdToCode)
const housingFromCode = reverseMap(housingToCode)
const incomeFromCode = reverseMap(incomeToCode)

// 여러 UI 라벨이 같은 Enum을 가리키는 경우에는 화면에서 사용할 대표 라벨을 고정한다.
employmentFromCode.ON_LEAVE = '휴직 중'

export function toUserProfilePatch(
  profile: UserProfileUpdate,
  onboardingCompleted?: boolean,
): UserProfilePatch {
  const payload: UserProfilePatch = {}
  if (profile.birthYear !== undefined) payload.birth_year = profile.birthYear
  if (profile.regionName !== undefined) payload.region_sido = profile.regionName
  if (profile.incomeBracket !== undefined) {
    payload.income_band_code = incomeToCode[profile.incomeBracket] ?? 'UNKNOWN'
  }
  if (profile.employment !== undefined) {
    payload.employment_status_code = employmentToCode[profile.employment] ?? 'OTHER'
  }
  if (profile.householdType !== undefined) {
    payload.household_type_code = householdToCode[profile.householdType] ?? 'OTHER'
  }
  if (profile.housingType !== undefined) {
    payload.housing_type_code = housingToCode[profile.housingType] ?? 'OTHER'
  }
  if (onboardingCompleted !== undefined) payload.onboarding_completed = onboardingCompleted
  return payload
}

export function fromUserProfileResponse(
  response: UserProfileResponse,
  current: UserProfile,
): UserProfile {
  const birthYear = response.birth_year ?? current.birthYear
  const housingType = response.housing_type_code
    ? (housingFromCode[response.housing_type_code] ?? current.housingType)
    : current.housingType
  return {
    ...current,
    id: String(response.user_id),
    birthYear,
    age: new Date().getFullYear() - birthYear,
    regionName: response.region_sido ?? current.regionName,
    region: {
      city: response.region_sido ?? current.region.city,
      district: response.region_sigungu ?? current.region.district,
    },
    incomeBracket: response.income_band_code
      ? (incomeFromCode[response.income_band_code] ?? current.incomeBracket)
      : current.incomeBracket,
    employment: response.employment_status_code
      ? (employmentFromCode[response.employment_status_code] ?? current.employment)
      : current.employment,
    householdType: response.household_type_code
      ? (householdFromCode[response.household_type_code] ?? current.householdType)
      : current.householdType,
    housingType,
    housing: {
      ...current.housing,
      type: housingType,
    },
  }
}
