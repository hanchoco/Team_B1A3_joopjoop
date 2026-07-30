import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function FinanceSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        대출 원금(원)
        <input
          name="principal"
          type="number"
          min={0}
          value={values.principal ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        연 이자율(%)
        <input
          name="annualInterestRate"
          type="number"
          min={0}
          max={100}
          value={values.annualInterestRate ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        이자 감면율(%)
        <input name="interestReductionRate" type="number" min={0} max={100} value={values.interestReductionRate ?? 0} onChange={update} className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal" />
      </label>
      <label className="text-sm font-semibold">
        지원 기간(개월)
        <input name="supportMonths" type="number" min={1} max={120} value={values.supportMonths ?? 12} onChange={update} className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal" />
      </label>
    </div>
  )
}
