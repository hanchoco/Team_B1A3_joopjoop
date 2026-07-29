import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function HousingSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="text-sm font-semibold">
        월세
        <input
          name="monthlyRent"
          type="number"
          min={0}
          value={values.monthlyRent ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        월 관리비
        <input
          name="maintenanceFee"
          type="number"
          min={0}
          value={values.maintenanceFee ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        보증금
        <input
          name="deposit"
          type="number"
          min={0}
          value={values.deposit ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
