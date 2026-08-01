import type { ChangeEvent } from 'react'
import type { HousingRentRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import CurrencyInput from './CurrencyInput'
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
          ...(r.support_months !== undefined
            ? [{ label: '지원 기간', value: `${r.support_months}개월` }]
            : []),
          ...(r.rent_limit_amount !== undefined
            ? [{ label: '월세 제한', value: formatWon(r.rent_limit_amount) }]
            : []),
          ...(r.deposit_limit_amount !== undefined
            ? [{ label: '보증금 제한', value: formatWon(r.deposit_limit_amount) }]
            : []),
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <CurrencyInput
          name="monthly_rent_amount"
          label="월세"
          required
          placeholder="예: 500,000"
          value={values.monthly_rent_amount}
          onChange={onChange}
        />
        <CurrencyInput
          name="monthly_management_fee_amount"
          label="월 관리비(선택, 지원 대상 아님)"
          placeholder="예: 100,000"
          value={values.monthly_management_fee_amount ?? 0}
          onChange={onChange}
          note="관리비는 지원 계산에 포함되지 않으며 참고용으로만 기록돼요."
        />
        <CurrencyInput
          name="deposit_amount"
          label="보증금(선택)"
          placeholder="예: 10,000,000"
          value={values.deposit_amount ?? 0}
          onChange={onChange}
        />
        <label className="text-sm font-semibold">
          희망 지원 개월 수(선택)
          <div className="relative mt-2">
            <input
              name="support_months"
              type="number"
              min={1}
              max={r.support_months}
              value={values.support_months ?? r.support_months}
              onChange={update}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 pr-14 font-normal"
            />
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-gray-400">
              개월
            </span>
          </div>
        </label>
      </div>
    </div>
  )
}
