import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function TransportSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        월평균 대중교통비(원)
        <input
          name="monthlyTransportCost"
          type="number"
          min={0}
          value={values.monthlyTransportCost ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        환급률(%)
        <input
          name="reimbursementRate"
          type="number"
          min={0}
          max={100}
          value={values.reimbursementRate ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        월 지원 한도(원)
        <input
          name="supportCap"
          type="number"
          min={0}
          value={values.supportCap ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        지원 기간(개월)
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
