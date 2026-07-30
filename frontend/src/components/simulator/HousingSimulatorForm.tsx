import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function HousingSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        월세
        <input
          name="monthly_rent_amount"
          type="number"
          min={0}
          value={values.monthly_rent_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        월 관리비
        <input
          name="monthly_management_fee_amount"
          type="number"
          min={0}
          value={values.monthly_management_fee_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        보증금
        <input
          name="deposit_amount"
          type="number"
          min={0}
          value={values.deposit_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        정책 월 지원금
        <input
          name="monthly_support_amount"
          type="number"
          min={0}
          value={values.monthly_support_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
