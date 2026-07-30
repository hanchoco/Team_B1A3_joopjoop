import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function EmploymentSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        현재 월 소득
        <input
          name="monthly_income_amount"
          type="number"
          min={0}
          value={values.monthly_income_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        정책 월 지원금
        <input
          name="monthly_subsidy_amount"
          type="number"
          min={0}
          value={values.monthly_subsidy_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
