import type { ChangeEvent } from 'react'
import type { SimulatorFormProps } from '../../types/simulator'

export default function WelfareSimulatorForm({ values, onChange }: SimulatorFormProps) {
  const update = (event: ChangeEvent<HTMLInputElement>) =>
    onChange(event.target.name, Number(event.target.value))

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">
        월 필수 생활비(원)
        <input
          name="monthlyLivingCost"
          type="number"
          min={0}
          value={values.monthlyLivingCost ?? 0}
          onChange={update}
          className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
        />
      </label>
      <label className="text-sm font-semibold">
        월 복지 혜택(원)
        <input
          name="monthlyBenefit"
          type="number"
          min={0}
          value={values.monthlyBenefit ?? 0}
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
