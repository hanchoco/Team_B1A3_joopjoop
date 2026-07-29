import { ArrowLeft, ArrowRight, TrendingDown } from 'lucide-react'
import { useState } from 'react'
import type { ComponentType } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import EmploymentSimulatorForm from '../../components/simulator/EmploymentSimulatorForm'
import FinanceSimulatorForm from '../../components/simulator/FinanceSimulatorForm'
import HousingSimulatorForm from '../../components/simulator/HousingSimulatorForm'
import TaxSimulatorForm from '../../components/simulator/TaxSimulatorForm'
import TransportSimulatorForm from '../../components/simulator/TransportSimulatorForm'
import WelfareSimulatorForm from '../../components/simulator/WelfareSimulatorForm'
import type { SimulatorFormProps, SimulatorInputValue } from '../../types/simulator'
import mockData from '../../utils/mockData.json'

const toManWon = (amount: number) => amount / 10000

type SimulatorCategory = 'housing' | 'transport' | 'finance' | 'tax' | 'employment' | 'welfare'

const simulatorForms: Record<SimulatorCategory, ComponentType<SimulatorFormProps>> = {
  housing: HousingSimulatorForm,
  transport: TransportSimulatorForm,
  finance: FinanceSimulatorForm,
  tax: TaxSimulatorForm,
  employment: EmploymentSimulatorForm,
  welfare: WelfareSimulatorForm,
}

const policyCategories: Record<string, SimulatorCategory> = {
  'youth-rent': 'housing',
  transport: 'transport',
  'youth-account': 'finance',
  'tax-credit': 'tax',
  'employment-support': 'employment',
  'welfare-support': 'welfare',
}

export default function Simulator() {
  const [period, setPeriod] = useState('월 기준')
  const [formValues, setFormValues] = useState<Record<string, SimulatorInputValue>>({})
  const navigate = useNavigate()
  const { id } = useParams()
  const category = policyCategories[id ?? 'youth-rent'] ?? 'housing'
  const CategoryForm = simulatorForms[category]
  const { before, after, monthlySavings, annualSavings } = mockData.savingsSimulation
  const yearly = period === '연 기준'
  const beforeAmount = toManWon(before.housingCost) * (yearly ? 12 : 1)
  const afterAmount = toManWon(after.housingCost) * (yearly ? 12 : 1)
  const savedAmount = toManWon(yearly ? annualSavings : monthlySavings)

  function updateFormValue(name: string, value: SimulatorInputValue) {
    setFormValues((current) => ({ ...current, [name]: value }))
  }

  return (
    <section className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={() => navigate(`/policies/${id}`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 정책 상세로
      </button>

      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">혜택 계산기</p>
        <h1 className="mt-2 text-3xl font-black">예상 시뮬레이션</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          이 정책을 받으면 생활비가 어떻게 달라지는지 한눈에 확인해보세요.
        </p>
      </div>

      <div className="mt-6 border-y border-gray-200 py-6">
        <h2 className="mb-4 text-lg font-bold">시뮬레이션 조건</h2>
        <CategoryForm values={formValues} onChange={updateFormValue} />
      </div>

      <div className="mt-6 inline-flex rounded-lg bg-slate-100 p-1">
        {['월 기준', '연 기준'].map((item) => (
          <button
            type="button"
            key={item}
            onClick={() => setPeriod(item)}
            className={`rounded-md px-6 py-2 text-sm font-bold ${
              period === item ? 'bg-blue-600 text-white' : 'text-gray-500'
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="mt-5 grid items-stretch gap-4 md:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <p className="text-sm font-semibold text-gray-500">지원 전 · Before</p>
          <p className="mt-5 text-4xl font-black">{beforeAmount.toLocaleString()}만 원</p>
          <p className="mt-6 border-t pt-5 text-sm text-gray-500">현재 주거비 기준</p>
        </div>
        <div className="grid place-items-center">
          <ArrowRight className="rotate-90 text-blue-600 md:rotate-0" />
        </div>
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
          <p className="text-sm font-semibold text-blue-700">지원 후 · After</p>
          <p className="mt-5 text-4xl font-black text-blue-700">
            {afterAmount.toLocaleString()}만 원
          </p>
          <p className="mt-6 border-t border-blue-200 pt-5 text-sm text-blue-700">
            지원금 반영 후 예상 금액
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-col items-center rounded-xl border border-blue-200 bg-white p-6 text-center">
        <TrendingDown className="text-blue-600" />
        <p className="mt-3 text-sm text-gray-500">{period} 총 절감 금액</p>
        <p className="mt-1 text-3xl font-black text-blue-600">
          +{savedAmount.toLocaleString()}만 원
        </p>
      </div>

      <p className="mt-4 rounded-lg bg-slate-50 p-4 text-xs leading-6 text-gray-500">
        이 결과는 저장된 프로필과 가상 정책 데이터를 바탕으로 계산한 예상 금액이에요. 실제 지급
        금액은 심사 결과에 따라 달라질 수 있어요.
      </p>
    </section>
  )
}
