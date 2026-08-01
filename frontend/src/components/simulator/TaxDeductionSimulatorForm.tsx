import type { ChangeEvent } from 'react'
import type { TaxDeductionRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import KnownRuleInfo from './KnownRuleInfo'

const DEDUCTION_TYPE_LABEL: Record<string, string> = {
  TAX_CREDIT: '세액공제',
  INCOME_DEDUCTION: '소득공제',
}

export default function TaxDeductionSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as TaxDeductionRuleJson
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, event.target.value === '' ? undefined : Number(event.target.value))

  return (
    <div>
      <KnownRuleInfo
        items={[
          { label: '공제율', value: `${r.deduction_rate_percent}%` },
          ...(r.max_deduction_amount !== undefined
            ? [{ label: '공제한도', value: formatWon(r.max_deduction_amount) }]
            : []),
          {
            label: '공제 방식',
            value: DEDUCTION_TYPE_LABEL[r.deduction_type] ?? r.deduction_type,
          },
        ]}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold">
          연간 세액/과세표준
          <input
            name="annual_tax_amount"
            type="number"
            min={0}
            required
            value={values.annual_tax_amount ?? ''}
            onChange={update}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
      </div>
    </div>
  )
}
