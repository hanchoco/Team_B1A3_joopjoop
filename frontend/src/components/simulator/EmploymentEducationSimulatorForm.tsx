import type { EmploymentEducationRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import { hasValue } from '../../utils/hasValue'
import CurrencyInput from './CurrencyInput'
import KnownRuleInfo from './KnownRuleInfo'

export default function EmploymentEducationSimulatorForm({
  rule,
  values,
  onChange,
}: SimulatorFormProps) {
  const r = rule as unknown as EmploymentEducationRuleJson

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(hasValue(r.training_allowance_amount)
            ? [{ label: '훈련수당', value: formatWon(r.training_allowance_amount) }]
            : []),
          ...(hasValue(r.education_subsidy_amount)
            ? [{ label: '교육비 지원액', value: formatWon(r.education_subsidy_amount) }]
            : []),
          ...(hasValue(r.employment_success_bonus_amount)
            ? [{ label: '취업성공수당', value: formatWon(r.employment_success_bonus_amount) }]
            : []),
          ...(hasValue(r.support_months)
            ? [{ label: '지원 기간', value: `${r.support_months}개월` }]
            : []),
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <CurrencyInput
          name="current_monthly_income_amount"
          label="현재 월 소득(선택)"
          placeholder="예: 2,000,000"
          value={values.current_monthly_income_amount ?? 0}
          onChange={onChange}
        />
      </div>
    </div>
  )
}
