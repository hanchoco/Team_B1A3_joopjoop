import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function TaxSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        연간 납부 세액(원)
        <input
          name="annualTaxPaid"
          type="number"
          min={0}
          value={values.annualTaxPaid ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        세금 감면율(%)
        <input
          name="taxReductionRate"
          type="number"
          min={0}
          max={100}
          value={values.taxReductionRate ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        최대 감면액(원)
        <input
          name="maxReduction"
          type="number"
          min={0}
          value={values.maxReduction ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        적용 기간(개월)
        <input
          name="supportMonths"
          type="number"
          min={1}
          max={120}
          value={values.supportMonths ?? 12}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
