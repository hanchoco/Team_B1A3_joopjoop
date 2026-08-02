import type { TaxDeductionRuleJson } from '../../types/api'
import type { SimulatorFormProps } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import CurrencyInput from './CurrencyInput'
import KnownRuleInfo from './KnownRuleInfo'

const DEDUCTION_TYPE_LABEL: Record<string, string> = {
  TAX_CREDIT: '세액공제',
  INCOME_DEDUCTION: '소득공제',
}

export default function TaxDeductionSimulatorForm({ rule, values, onChange }: SimulatorFormProps) {
  const r = rule as unknown as TaxDeductionRuleJson

  return (
    <div>
      <KnownRuleInfo
        items={[
          ...(r.deduction_rate_percent !== undefined
            ? [{ label: '공제율', value: `${r.deduction_rate_percent}%` }]
            : []),
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
        <CurrencyInput
          name="annual_tax_amount"
          label="연간 세액/과세표준"
          required
          placeholder="예: 1,000,000"
          value={values.annual_tax_amount}
          onChange={onChange}
        />
      </div>
    </div>
  )
}
