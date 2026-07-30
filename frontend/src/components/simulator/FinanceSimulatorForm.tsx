import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function FinanceSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="text-sm font-semibold">
        대출/저축 원금
        <input
          name="principal_amount"
          type="number"
          min={0}
          value={values.principal_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        연 이자율(%)
        <input
          name="annual_interest_rate_percent"
          type="number"
          min={0}
          max={100}
          step={0.01}
          value={values.annual_interest_rate_percent ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        정책 이자 감면율(%)
        <input
          name="interest_reduction_rate_percent"
          type="number"
          min={0}
          max={100}
          step={0.01}
          value={values.interest_reduction_rate_percent ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
