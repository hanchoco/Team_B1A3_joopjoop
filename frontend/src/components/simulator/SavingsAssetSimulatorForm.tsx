import type { SavingsAssetRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import CurrencyInput from './CurrencyInput'
import KnownRuleInfo from './KnownRuleInfo'

export default function SavingsAssetSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as SavingsAssetRuleJson

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
        <CurrencyInput
          name="monthly_deposit_amount"
          label="매월 납입 예정 금액"
          required
          placeholder="예: 100,000"
          value={values.monthly_deposit_amount}
          onChange={onChange}
        />
      </div>
    </div>
  )
}
