import { ArrowLeft, ArrowRight, TrendingDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ComponentType } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import EmploymentSimulatorForm from '../../components/simulator/EmploymentSimulatorForm'
import FinanceSimulatorForm from '../../components/simulator/FinanceSimulatorForm'
import HousingSimulatorForm from '../../components/simulator/HousingSimulatorForm'
import TaxSimulatorForm from '../../components/simulator/TaxSimulatorForm'
import TransportSimulatorForm from '../../components/simulator/TransportSimulatorForm'
import WelfareSimulatorForm from '../../components/simulator/WelfareSimulatorForm'
import { getPolicyDetail } from '../../api/policies'
import {
  runSimulation,
  type SimulatorCategory,
  type SimulatorPayload,
  type SimulatorResult,
} from '../../api/simulator'
import type { SimulatorFormProps, SimulatorInputValue } from '../../types/simulator'

const toManWon = (amount: number) => amount / 10000

const simulatorForms: Record<SimulatorCategory, ComponentType<SimulatorFormProps>> = {
  housing: HousingSimulatorForm,
  transport: TransportSimulatorForm,
  finance: FinanceSimulatorForm,
  tax: TaxSimulatorForm,
  employment: EmploymentSimulatorForm,
  welfare: WelfareSimulatorForm,
}

const categoryCodeMap: Record<string, SimulatorCategory> = {
  HOUSING: 'housing',
  TRANSPORT: 'transport',
  FINANCE: 'finance',
  TAX: 'tax',
  EMPLOYMENT: 'employment',
  WELFARE: 'welfare',
}

function numberValue(
  values: Record<string, SimulatorInputValue>,
  key: string,
  fallback = 0,
): number {
  const value = Number(values[key] ?? fallback)
  return Number.isFinite(value) ? value : fallback
}

function buildPayload(
  category: SimulatorCategory,
  values: Record<string, SimulatorInputValue>,
): SimulatorPayload {
  const supportMonths = numberValue(values, 'supportMonths', 12)
  if (category === 'housing') {
    return {
      monthly_rent_amount: numberValue(values, 'monthlyRent'),
      monthly_management_fee_amount: numberValue(values, 'maintenanceFee'),
      deposit_amount: numberValue(values, 'deposit'),
      monthly_support_amount: numberValue(values, 'monthlySupport'),
      support_months: supportMonths,
    }
  }
  if (category === 'transport') {
    return {
      monthly_transport_cost_amount: numberValue(values, 'monthlyTransportCost'),
      reimbursement_rate_percent: numberValue(values, 'reimbursementRate'),
      monthly_support_cap_amount: numberValue(values, 'supportCap'),
      support_months: supportMonths,
    }
  }
  if (category === 'finance') {
    return {
      principal_amount: numberValue(values, 'principal'),
      annual_interest_rate_percent: numberValue(values, 'annualInterestRate'),
      interest_reduction_rate_percent: numberValue(values, 'interestReductionRate'),
      support_months: supportMonths,
    }
  }
  if (category === 'tax') {
    return {
      annual_tax_amount: numberValue(values, 'annualTaxPaid'),
      tax_reduction_rate_percent: numberValue(values, 'taxReductionRate'),
      max_reduction_amount: numberValue(values, 'maxReduction'),
      support_months: supportMonths,
    }
  }
  if (category === 'employment') {
    return {
      monthly_income_amount: numberValue(values, 'monthlySalary'),
      monthly_subsidy_amount: numberValue(values, 'monthlySubsidy'),
      support_months: supportMonths,
    }
  }
  return {
    monthly_living_cost_amount: numberValue(values, 'monthlyLivingCost'),
    monthly_benefit_amount: numberValue(values, 'monthlyBenefit'),
    support_months: supportMonths,
  }
}

export default function Simulator() {
  const [period, setPeriod] = useState('월 기준')
  const [formValues, setFormValues] = useState<Record<string, SimulatorInputValue>>({})
  const [result, setResult] = useState<SimulatorResult | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [error, setError] = useState('')
  const [category, setCategory] = useState<SimulatorCategory | null>(null)
  const navigate = useNavigate()
  const { id } = useParams()
  const policyId = Number(id ?? 1)
  const CategoryForm = category ? simulatorForms[category] : null
  const yearly = period === '연 기준'
  const beforeAmount = result
    ? toManWon(Number(yearly ? result.annual_before_amount : result.monthly_before_amount))
    : 0
  const afterAmount = result
    ? toManWon(Number(yearly ? result.annual_after_amount : result.monthly_after_amount))
    : 0
  const savedAmount = result
    ? toManWon(Number(yearly ? result.annual_savings_amount : result.monthly_savings_amount))
    : 0

  useEffect(() => {
    let isCurrent = true
    getPolicyDetail(policyId)
      .then((policy) => {
        const primaryCategory = policy.categories.find((item) => item.is_primary)
        const resolvedCategory = primaryCategory ? categoryCodeMap[primaryCategory.code] : undefined
        if (isCurrent) setCategory(resolvedCategory ?? 'housing')
      })
      .catch(() => {
        if (isCurrent) setError('정책 카테고리를 확인하지 못했어요.')
      })
    return () => {
      isCurrent = false
    }
  }, [policyId])

  function updateFormValue(name: string, value: SimulatorInputValue) {
    setFormValues((current) => ({ ...current, [name]: value }))
    setResult(null)
    setError('')
  }

  async function calculate(): Promise<void> {
    if (!category) return
    setIsCalculating(true)
    setError('')
    try {
      setResult(await runSimulation(category, buildPayload(category, formValues)))
    } catch {
      setError('혜택을 계산하지 못했어요. 입력값을 확인하고 다시 시도해 주세요.')
    } finally {
      setIsCalculating(false)
    }
  }

  if (!CategoryForm || !category) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-3">
        <span className="h-8 w-8 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
        <p className="text-sm text-amber-900">{error || '계산기를 준비하고 있어요.'}</p>
      </div>
    )
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
        <button
          type="button"
          disabled={isCalculating}
          onClick={() => void calculate()}
          className="mt-5 w-full rounded-lg bg-blue-600 py-3.5 font-bold text-white disabled:bg-blue-300"
        >
          {isCalculating ? '혜택을 계산하고 있어요...' : '예상 혜택 계산하기'}
        </button>
        {error && <p className="mt-3 text-sm font-semibold text-rose-600">{error}</p>}
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

      {result ? (
        <>
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
            {result.disclaimer}
          </p>
        </>
      ) : (
        <p className="mt-5 rounded-xl bg-amber-50 p-6 text-center text-sm text-amber-900">
          값을 입력하고 계산 버튼을 누르면 월간·연간 예상 혜택을 보여드릴게요.
        </p>
      )}
    </section>
  )
}
