import type { ChangeEvent } from 'react'
import type { EmploymentEducationRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import KnownRuleInfo from './KnownRuleInfo'

export default function EmploymentEducationSimulatorForm({
  rule,
  values,
  onChange,
}: SimulatorFormProps) {
  const r = rule as unknown as EmploymentEducationRuleJson
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, event.target.value === '' ? undefined : Number(event.target.value))

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(r.training_allowance_amount !== undefined
            ? [{ label: '훈련수당', value: formatWon(r.training_allowance_amount) }]
            : []),
          ...(r.education_subsidy_amount !== undefined
            ? [{ label: '교육비 지원액', value: formatWon(r.education_subsidy_amount) }]
            : []),
          ...(r.employment_success_bonus_amount !== undefined
            ? [{ label: '취업성공수당', value: formatWon(r.employment_success_bonus_amount) }]
            : []),
          ...(r.support_months !== undefined
            ? [{ label: '지원 기간', value: `${r.support_months}개월` }]
            : []),
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          현재 월 소득(선택)
          <div className="relative mt-2">
            <input
              name="current_monthly_income_amount"
              type="number"
              min={0}
              step={10000}
              value={values.current_monthly_income_amount ?? 0}
              onChange={update}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 pr-10 font-normal"
            />
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">
              원
            </span>
          </div>
        </label>
      </div>
    </div>
  )
}
