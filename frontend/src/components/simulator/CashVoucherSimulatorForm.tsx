import type { ChangeEvent } from 'react'
import type { CashVoucherRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import KnownRuleInfo from './KnownRuleInfo'

const PAYMENT_CYCLE_LABEL: Record<string, string> = {
  ONCE: '1회',
  MONTHLY: '매월',
  YEARLY: '매년',
  MATURITY: '만기 시',
  VARIABLE: '변동',
}

export default function CashVoucherSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as CashVoucherRuleJson
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, event.target.value === '' ? undefined : Number(event.target.value))
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
            <label className="text-sm font-semibold">
              받고 싶은 개월 수(선택)
              <input
                name="count"
                type="number"
                min={1}
                max={r.max_count}
                value={values.count ?? r.max_count}
                onChange={update}
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
              />
            </label>
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <KnownRuleInfo
        items={[
          { label: '지원 비율', value: `${r.rate_percent}%` },
          { label: '지원 상한액', value: formatWon(r.cap_amount) },
          { label: '지급 주기', value: cycleLabel },
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          지출/구매 금액
          <input
            name="base_amount"
            type="number"
            min={0}
            required
            value={values.base_amount ?? ''}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
        {isMonthly && (
          <label className="text-sm font-semibold">
            받고 싶은 개월 수(선택)
            <input
              name="count"
              type="number"
              min={1}
              value={values.count ?? 1}
              onChange={update}
              className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
            />
          </label>
        )}
      </div>
    </div>
  )
}
