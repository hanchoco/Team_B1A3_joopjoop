import type { HousingRentRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import { hasValue } from '../../utils/hasValue'
import CurrencyInput from './CurrencyInput'
import KnownRuleInfo from './KnownRuleInfo'
import PositiveIntegerInput from './PositiveIntegerInput'

export default function HousingRentSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as HousingRentRuleJson

  return (
    <div>
      <KnownRuleInfo
        items={[
          { label: '월 지원 한도', value: formatWon(r.monthly_support_cap_amount) },
          ...(hasValue(r.support_months)
            ? [{ label: '지원 기간', value: `${r.support_months}개월` }]
            : []),
          ...(hasValue(r.rent_limit_amount)
            ? [{ label: '월세 제한', value: formatWon(r.rent_limit_amount) }]
            : []),
          ...(hasValue(r.deposit_limit_amount)
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
        <PositiveIntegerInput
          name="support_months"
          label="희망 지원 개월 수(선택)"
          value={values.support_months}
          initialValue={r.support_months}
          max={r.support_months}
          onChange={onChange}
        />
      </div>
    </div>
  )
}
