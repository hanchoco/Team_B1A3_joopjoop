import type { EmploymentEducationRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import { hasValue } from '../../utils/hasValue'
import KnownRuleInfo from './KnownRuleInfo'

export default function EmploymentEducationSimulatorForm({ rule }: SimulatorFormProps) {
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
    </div>
  )
}
