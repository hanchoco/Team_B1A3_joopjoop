import type { ChangeEvent } from 'react'
import type { LoanInterestRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import KnownRuleInfo from './KnownRuleInfo'
import PercentInput from './PercentInput'

const REPAYMENT_TYPE_LABEL: Record<string, string> = {
  EQUAL_PRINCIPAL_INTEREST: '원리금균등상환',
  EQUAL_PRINCIPAL: '원금균등상환',
  BULLET: '만기일시상환',
}

export default function LoanInterestSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as LoanInterestRuleJson
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, event.target.value === '' ? undefined : Number(event.target.value))
  const needsGeneralRate = r.interest_reduction_rate_percent === undefined

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(r.policy_interest_rate_percent !== undefined
            ? [{ label: '정책 확정 금리', value: `${r.policy_interest_rate_percent}%` }]
            : []),
          ...(r.interest_reduction_rate_percent !== undefined
            ? [{ label: '일반 대출 대비 감면율', value: `${r.interest_reduction_rate_percent}%` }]
            : []),
          { label: '최대 대출한도', value: formatWon(r.max_loan_amount) },
          ...(r.max_support_months !== undefined
            ? [{ label: '최대 지원기간', value: `${r.max_support_months}개월` }]
            : []),
          {
            label: '상환 방식',
            value: REPAYMENT_TYPE_LABEL[r.repayment_type] ?? r.repayment_type,
          },
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          대출 신청 금액
          <input
            name="loan_amount"
            type="number"
            min={0}
            required
            value={values.loan_amount ?? ''}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
        {needsGeneralRate && (
          <PercentInput
            name="general_interest_rate_percent"
            label="일반 대출 금리"
            value={values.general_interest_rate_percent ?? 0}
            onChange={onChange}
          />
        )}
        <label className="text-sm font-semibold">
          희망 지원 개월 수(선택)
          <input
            name="support_months"
            type="number"
            min={1}
            max={r.max_support_months}
            value={values.support_months ?? r.max_support_months}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
      </div>
    </div>
  )
}
