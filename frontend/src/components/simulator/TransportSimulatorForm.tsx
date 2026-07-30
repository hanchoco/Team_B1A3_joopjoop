import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function TransportSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="text-sm font-semibold">
        월평균 대중교통비
        <input
          name="monthly_transport_cost_amount"
          type="number"
          min={0}
          value={values.monthly_transport_cost_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        정책 환급률(%)
        <input
          name="reimbursement_rate_percent"
          type="number"
          min={0}
          max={100}
          value={values.reimbursement_rate_percent ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        월 지원 한도(선택)
        <input
          name="monthly_support_cap_amount"
          type="number"
          min={0}
          value={values.monthly_support_cap_amount ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
    </div>
  )
}
