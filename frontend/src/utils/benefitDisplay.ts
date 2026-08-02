import type { PolicyBenefitResponse, PolicySummaryResponse } from '../types/api'

export const MIN_UNTYPED_BENEFIT_AMOUNT_KRW = 1_000

type BenefitDisplayPolicy = Pick<PolicySummaryResponse, 'estimated_benefit_amount'> & {
  benefits?: readonly PolicyBenefitResponse[]
}

export type BenefitDisplay =
  | {
      kind: 'amount'
      label: '최대 예상 혜택'
      displayValue: string
    }
  | {
      kind: 'rate'
      label: '금리' | '비율'
      displayValue: string
    }
  | {
      kind: 'hidden'
    }

const RATE_FIELDS = [
  { key: 'policy_interest_rate_percent', label: '금리' },
  { key: 'interest_reduction_rate_percent', label: '금리' },
  { key: 'base_interest_rate_percent', label: '금리' },
  { key: 'bonus_interest_rate_percent', label: '금리' },
  { key: 'government_match_rate_percent', label: '비율' },
  { key: 'rate_percent', label: '비율' },
  { key: 'deduction_rate_percent', label: '비율' },
] as const

const AMOUNT_FIELDS = [
  'max_loan_amount',
  'monthly_max_support_amount',
  'amount',
  'cap_amount',
  'monthly_support_cap_amount',
  'training_allowance_amount',
  'education_subsidy_amount',
  'employment_success_bonus_amount',
  'max_deduction_amount',
] as const

const PERCENT_VALUE_PATTERN = /(\d[\d,]*(?:\.\d+)?)\s*%/g
const WON_VALUE_PATTERN = /(\d[\d,]*(?:\.\d+)?)\s*원/g
const INTEREST_RATE_PATTERN = /금리|이자율/

function toFinitePositiveNumber(value: unknown): number | null {
  if (typeof value !== 'number' && typeof value !== 'string') return null
  if (typeof value === 'string' && value.trim() === '') return null

  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null
}

function numbersMatch(left: number, right: number): boolean {
  return Math.abs(left - right) <= Number.EPSILON * Math.max(1, Math.abs(left), Math.abs(right))
}

function readField(record: object, key: string): unknown {
  return Reflect.get(record, key) as unknown
}

function matchesStoredBenefitValue(benefit: PolicyBenefitResponse, value: number): boolean {
  return [benefit.max_total_amount, benefit.max_amount].some((candidate) => {
    const numeric = toFinitePositiveNumber(candidate)
    return numeric !== null && numbersMatch(numeric, value)
  })
}

function extractUnitValues(text: string, pattern: RegExp): number[] {
  return Array.from(text.matchAll(pattern), (match) => Number(match[1].replaceAll(',', ''))).filter(
    Number.isFinite,
  )
}

function getExplicitRateDisplay(
  benefits: readonly PolicyBenefitResponse[],
  value: number,
): Extract<BenefitDisplay, { kind: 'rate' }> | null {
  for (const benefit of benefits) {
    if (!matchesStoredBenefitValue(benefit, value)) continue

    const rule = benefit.calculation_rule_json
    if (rule) {
      for (const field of RATE_FIELDS) {
        const candidate = toFinitePositiveNumber(readField(rule, field.key))
        if (candidate !== null && numbersMatch(candidate, value)) {
          return {
            kind: 'rate',
            label: field.label,
            displayValue: `${value.toLocaleString('ko-KR', { maximumFractionDigits: 20 })}%`,
          }
        }
      }
    }

    if (!benefit.display_text) continue
    const percentValues = extractUnitValues(benefit.display_text, PERCENT_VALUE_PATTERN)
    if (percentValues.some((candidate) => numbersMatch(candidate, value))) {
      return {
        kind: 'rate',
        label: INTEREST_RATE_PATTERN.test(benefit.display_text) ? '금리' : '비율',
        displayValue: `${value.toLocaleString('ko-KR', { maximumFractionDigits: 20 })}%`,
      }
    }
  }
  return null
}

function hasExplicitAmountMetadata(
  benefits: readonly PolicyBenefitResponse[],
  value: number,
): boolean {
  const contributingBenefits = benefits.filter((benefit) =>
    [benefit.max_total_amount, benefit.max_amount].some(
      (candidate) => toFinitePositiveNumber(candidate) !== null,
    ),
  )

  if (
    contributingBenefits.length > 0 &&
    contributingBenefits.every((benefit) => benefit.benefit_type === 'CASH')
  ) {
    return true
  }

  return benefits.some((benefit) => {
    if (!matchesStoredBenefitValue(benefit, value)) return false

    const rule = benefit.calculation_rule_json
    if (
      rule &&
      AMOUNT_FIELDS.some((field) => {
        const candidate = toFinitePositiveNumber(readField(rule, field))
        return candidate !== null && numbersMatch(candidate, value)
      })
    ) {
      return true
    }

    if (!benefit.display_text) return false
    return extractUnitValues(benefit.display_text, WON_VALUE_PATTERN).some((candidate) =>
      numbersMatch(candidate, value),
    )
  })
}

function amountDisplay(value: number): Extract<BenefitDisplay, { kind: 'amount' }> {
  return {
    kind: 'amount',
    label: '최대 예상 혜택',
    displayValue: `${value.toLocaleString('ko-KR', { maximumFractionDigits: 20 })}원`,
  }
}

export function getBenefitDisplay(
  policy: BenefitDisplayPolicy,
  estimatedValue: unknown = policy.estimated_benefit_amount,
): BenefitDisplay {
  const numeric = toFinitePositiveNumber(estimatedValue)
  if (numeric === null) return { kind: 'hidden' }

  const benefits = policy.benefits ?? []
  const rateDisplay = getExplicitRateDisplay(benefits, numeric)
  if (rateDisplay) return rateDisplay

  if (hasExplicitAmountMetadata(benefits, numeric)) return amountDisplay(numeric)

  if (!Number.isInteger(numeric) || numeric < MIN_UNTYPED_BENEFIT_AMOUNT_KRW) {
    return { kind: 'hidden' }
  }

  return amountDisplay(numeric)
}
