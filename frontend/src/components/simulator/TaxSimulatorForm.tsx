import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function TaxSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="text-sm font-semibold">
        연간 납부세액
        <input
          name="annual_tax_amount"
          type="number"
          min={0}
          value={values.annual_tax_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        정책 감면율(%)
        <input
          name="tax_reduction_rate_percent"
          type="number"
          min={0}
          max={100}
          step={0.01}
          value={values.tax_reduction_rate_percent ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        최대 감면 한도(선택)
        <input
          name="max_reduction_amount"
          type="number"
          min={0}
          value={values.max_reduction_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
