import type { LoanInterestRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import { hasValue } from '../../utils/hasValue'
import CurrencyInput from './CurrencyInput'
import KnownRuleInfo from './KnownRuleInfo'
import PercentInput from './PercentInput'
import PositiveIntegerInput from './PositiveIntegerInput'

const REPAYMENT_TYPE_LABEL: Record<string, string> = {
  EQUAL_PRINCIPAL_INTEREST: '원리금균등상환',
  EQUAL_PRINCIPAL: '원금균등상환',
  BULLET: '만기일시상환',
}

export default function LoanInterestSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as LoanInterestRuleJson
  const needsGeneralRate = !hasValue(r.interest_reduction_rate_percent)

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(hasValue(r.policy_interest_rate_percent)
            ? [{ label: '정책 확정 금리', value: `${r.policy_interest_rate_percent}%` }]
            : []),
          ...(hasValue(r.interest_reduction_rate_percent)
            ? [{ label: '일반 대출 대비 감면율', value: `${r.interest_reduction_rate_percent}%` }]
            : []),
          { label: '최대 대출한도', value: formatWon(r.max_loan_amount) },
          ...(hasValue(r.max_support_months)
            ? [{ label: '최대 지원기간', value: `${r.max_support_months}개월` }]
            : []),
          {
            label: '상환 방식',
            value: REPAYMENT_TYPE_LABEL[r.repayment_type] ?? r.repayment_type,
          },
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <CurrencyInput
          name="loan_amount"
          label="대출 신청 금액"
          required
          placeholder="예: 10,000,000"
          value={values.loan_amount}
          onChange={onChange}
        />
        {needsGeneralRate && (
          <PercentInput
            name="general_interest_rate_percent"
            label="일반 대출 금리"
            value={values.general_interest_rate_percent ?? 0}
            onChange={onChange}
          />
        )}
        <PositiveIntegerInput
          name="support_months"
          label="희망 지원 개월 수(선택)"
          value={values.support_months}
          initialValue={r.max_support_months}
          max={r.max_support_months}
          onChange={onChange}
        />
      </div>
    </div>
  )
}
