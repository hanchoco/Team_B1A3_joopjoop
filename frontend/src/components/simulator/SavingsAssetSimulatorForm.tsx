import type { ChangeEvent } from 'react'
import type { SavingsAssetRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import KnownRuleInfo from './KnownRuleInfo'

export default function SavingsAssetSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as SavingsAssetRuleJson
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, event.target.value === '' ? undefined : Number(event.target.value))

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(r.government_match_rate_percent !== undefined
            ? [{ label: '정부매칭비율', value: `${r.government_match_rate_percent}%` }]
            : []),
          { label: '월 최대 지원금', value: formatWon(r.monthly_max_support_amount) },
          ...(r.maturity_months !== undefined
            ? [{ label: '만기 기간', value: `${r.maturity_months}개월` }]
            : []),
          ...(r.base_interest_rate_percent !== undefined
            ? [{ label: '기본금리', value: `${r.base_interest_rate_percent}%` }]
            : []),
          ...(r.bonus_interest_rate_percent !== undefined
            ? [{ label: '우대금리', value: `${r.bonus_interest_rate_percent}%` }]
            : []),
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          매월 납입 예정 금액
          <div className="relative mt-2">
            <input
              name="monthly_deposit_amount"
              type="number"
              min={0}
              step={10000}
              required
              value={values.monthly_deposit_amount ?? ''}
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
