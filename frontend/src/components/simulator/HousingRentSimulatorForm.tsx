import type { ChangeEvent } from 'react'
import type { HousingRentRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import KnownRuleInfo from './KnownRuleInfo'

export default function HousingRentSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as HousingRentRuleJson
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, event.target.value === '' ? undefined : Number(event.target.value))

  return (
    <div>
      <KnownRuleInfo
        items={[
          { label: '월 지원 한도', value: formatWon(r.monthly_support_cap_amount) },
          { label: '지원 기간', value: `${r.support_months}개월` },
          ...(r.rent_limit_amount !== undefined
            ? [{ label: '월세 제한', value: formatWon(r.rent_limit_amount) }]
            : []),
          ...(r.deposit_limit_amount !== undefined
            ? [{ label: '보증금 제한', value: formatWon(r.deposit_limit_amount) }]
            : []),
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          월세
          <input
            name="monthly_rent_amount"
            type="number"
            min={0}
            required
            value={values.monthly_rent_amount ?? ''}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
        <label className="text-sm font-semibold">
          월 관리비(선택, 지원 대상 아님)
          <input
            name="monthly_management_fee_amount"
            type="number"
            min={0}
            value={values.monthly_management_fee_amount ?? 0}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
          <p className="mt-1 text-xs font-normal text-gray-400">
            관리비는 지원 계산에 포함되지 않으며 참고용으로만 기록돼요.
          </p>
        </label>
        <label className="text-sm font-semibold">
          보증금(선택)
          <input
            name="deposit_amount"
            type="number"
            min={0}
            value={values.deposit_amount ?? 0}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
        <label className="text-sm font-semibold">
          희망 지원 개월 수(선택)
          <input
            name="support_months"
            type="number"
            min={1}
            max={r.support_months}
            value={values.support_months ?? r.support_months}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
      </div>
    </div>
  )
}
