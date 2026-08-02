import type { CashVoucherRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import { hasValue } from '../../utils/hasValue'
import CurrencyInput from './CurrencyInput'
import KnownRuleInfo from './KnownRuleInfo'
import PositiveIntegerInput from './PositiveIntegerInput'

const PAYMENT_CYCLE_LABEL: Record<string, string> = {
  ONCE: '1회',
  MONTHLY: '매월',
  YEARLY: '매년',
  MATURITY: '만기 시',
  VARIABLE: '변동',
}

export default function CashVoucherSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as CashVoucherRuleJson
  const cycleLabel = PAYMENT_CYCLE_LABEL[r.payment_cycle] ?? r.payment_cycle
  const isMonthly = r.payment_cycle === 'MONTHLY'

  if (r.amount_type === 'FIXED') {
    return (
      <div>
        <KnownRuleInfo
          items={[
            { label: '지급 금액', value: formatWon(r.amount) },
            { label: '지급 주기', value: cycleLabel },
            { label: '최대 지급 횟수', value: `${r.max_count}회` },
          ]}
        />
        {isMonthly && (
          <div className="grid gap-4 sm:grid-cols-2">
            <PositiveIntegerInput
              name="count"
              label="받고 싶은 개월 수(선택)"
              value={values.count}
              initialValue={r.max_count}
              max={r.max_count}
              onChange={onChange}
            />
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(hasValue(r.rate_percent)
            ? [{ label: '지원 비율', value: `${r.rate_percent}%` }]
            : []),
          { label: '지원 상한액', value: formatWon(r.cap_amount) },
          { label: '지급 주기', value: cycleLabel },
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <CurrencyInput
          name="base_amount"
          label="지출/구매 금액"
          required
          placeholder="예: 100,000"
          value={values.base_amount}
          onChange={onChange}
        />
        {isMonthly && (
          <PositiveIntegerInput
            name="count"
            label="받고 싶은 개월 수(선택)"
            value={values.count}
            onChange={onChange}
          />
        )}
      </div>
    </div>
  )
}
