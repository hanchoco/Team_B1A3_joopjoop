import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function HousingSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        월세(원)
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
        월 관리비(원)
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
        보증금(원)
        <input
          name="deposit"
          type="number"
          min={0}
          value={values.deposit ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        월 지원금(원)
        <input name="monthlySupport" type="number" min={0} value={values.monthlySupport ?? 0} onChange={update} className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal" />
      </label>
      <label className="text-sm font-semibold">
        지원 기간(개월)
        <input name="supportMonths" type="number" min={1} max={120} value={values.supportMonths ?? 12} onChange={update} className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal" />
      </label>
    </div>
  )
}
