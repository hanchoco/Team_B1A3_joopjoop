import { ArrowLeft, ArrowRight, TrendingDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ComponentType } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { extractErrorMessage } from '../../api/client'
import { getPolicy } from '../../api/policies'
import {
  simulateEmployment,
  simulateFinance,
  simulateHousing,
  simulateTax,
  simulateTransport,
  simulateWelfare,
} from '../../api/simulator'
import EmploymentSimulatorForm from '../../components/simulator/EmploymentSimulatorForm'
import FinanceSimulatorForm from '../../components/simulator/FinanceSimulatorForm'
import HousingSimulatorForm from '../../components/simulator/HousingSimulatorForm'
import TaxSimulatorForm from '../../components/simulator/TaxSimulatorForm'
import TransportSimulatorForm from '../../components/simulator/TransportSimulatorForm'
import WelfareSimulatorForm from '../../components/simulator/WelfareSimulatorForm'
import type { PolicyDetailResponse, SimulatorResult } from '../../types/api'
import type { SimulatorFormProps, SimulatorInputValue } from '../../types/simulator'

const toManWon = (amount: number | string) => Number(amount) / 10000

interface CategoryConfig {
  Form: ComponentType<SimulatorFormProps>
  benefitField: string | null
  simulate: (values: Record<string, number>) => Promise<SimulatorResult>
}

const CATEGORY_CONFIG: Record<string, CategoryConfig> = {
  HOUSING: {
    Form: HousingSimulatorForm,
    benefitField: 'monthly_support_amount',
    simulate: (v) =>
      simulateHousing({
        monthly_rent_amount: v.monthly_rent_amount ?? 0,
        monthly_management_fee_amount: v.monthly_management_fee_amount ?? 0,
        deposit_amount: v.deposit_amount ?? 0,
        monthly_support_amount: v.monthly_support_amount ?? 0,
        support_months: v.support_months ?? 12,
      }),
  },
  TRANSPORT: {
    Form: TransportSimulatorForm,
    benefitField: null,
    simulate: (v) =>
      simulateTransport({
        monthly_transport_cost_amount: v.monthly_transport_cost_amount ?? 0,
        reimbursement_rate_percent: v.reimbursement_rate_percent ?? 0,
        monthly_support_cap_amount: v.monthly_support_cap_amount || undefined,
        support_months: v.support_months ?? 12,
      }),
  },
  FINANCE: {
    Form: FinanceSimulatorForm,
    benefitField: null,
    simulate: (v) =>
      simulateFinance({
        principal_amount: v.principal_amount ?? 0,
        annual_interest_rate_percent: v.annual_interest_rate_percent ?? 0,
        interest_reduction_rate_percent: v.interest_reduction_rate_percent ?? 0,
        support_months: v.support_months ?? 12,
      }),
  },
  TAX: {
    Form: TaxSimulatorForm,
    benefitField: null,
    simulate: (v) =>
      simulateTax({
        annual_tax_amount: v.annual_tax_amount ?? 0,
        tax_reduction_rate_percent: v.tax_reduction_rate_percent ?? 0,
        max_reduction_amount: v.max_reduction_amount || undefined,
        support_months: v.support_months ?? 12,
      }),
  },
  EMPLOYMENT: {
    Form: EmploymentSimulatorForm,
    benefitField: 'monthly_subsidy_amount',
    simulate: (v) =>
      simulateEmployment({
        monthly_income_amount: v.monthly_income_amount ?? 0,
        monthly_subsidy_amount: v.monthly_subsidy_amount ?? 0,
        support_months: v.support_months ?? 12,
      }),
  },
  WELFARE: {
    Form: WelfareSimulatorForm,
    benefitField: 'monthly_benefit_amount',
    simulate: (v) =>
      simulateWelfare({
        monthly_living_cost_amount: v.monthly_living_cost_amount ?? 0,
        monthly_benefit_amount: v.monthly_benefit_amount ?? 0,
        support_months: v.support_months ?? 12,
      }),
  },
}

function estimateMonthlyBenefit(policy: PolicyDetailResponse): number {
  const monthlyBenefit = policy.benefits.find((benefit) => benefit.payment_cycle === 'MONTHLY')
  if (!monthlyBenefit) return 0
  const amount = monthlyBenefit.max_amount ?? monthlyBenefit.min_amount
  return amount !== null && amount !== undefined ? Number(amount) : 0
}

export default function Simulator() {
  const navigate = useNavigate()
  const { id } = useParams()
  const policyId = Number(id)

  const [policy, setPolicy] = useState<PolicyDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState<'월 기준' | '연 기준'>('월 기준')
  const [formValues, setFormValues] = useState<Record<string, SimulatorInputValue>>({
    support_months: 12,
  })
  const [result, setResult] = useState<SimulatorResult | null>(null)
  const [calculating, setCalculating] = useState(false)
  const [calcError, setCalcError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        if (!Number.isFinite(policyId)) {
          throw new Error('올바르지 않은 정책입니다.')
        }
        setLoading(true)
        setError('')
        return getPolicy(policyId)
      })
      .then((data) => {
        if (cancelled || !data) return
        setPolicy(data)
        const code = data.categories[0]?.code
        const config = code ? CATEGORY_CONFIG[code] : undefined
        if (config?.benefitField) {
          const field = config.benefitField
          setFormValues((current) => ({ ...current, [field]: estimateMonthlyBenefit(data) }))
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(extractErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [policyId])

  function updateFormValue(name: string, value: SimulatorInputValue) {
    setFormValues((current) => ({ ...current, [name]: value }))
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-gray-500">불러오는 중...</p>
  }
  if (error || !policy) {
    return (
      <section className="mx-auto max-w-4xl">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
        >
          <ArrowLeft size={16} /> 정책 상세로
        </button>
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error || '정책을 찾을 수 없습니다.'}
        </p>
      </section>
    )
  }

  const categoryCode = policy.categories[0]?.code
  const config = categoryCode ? CATEGORY_CONFIG[categoryCode] : undefined

  if (!config) {
    return (
      <section className="mx-auto max-w-4xl">
        <button
          onClick={() => navigate(`/policies/${policyId}`)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
        >
          <ArrowLeft size={16} /> 정책 상세로
        </button>
        <p className="mt-6 rounded-lg bg-slate-50 p-6 text-sm text-gray-600">
          이 정책은 아직 예상 시뮬레이션을 지원하지 않아요.
        </p>
      </section>
    )
  }

  async function calculate() {
    setCalculating(true)
    setCalcError('')
    try {
      const data = await config!.simulate(formValues as Record<string, number>)
      setResult(data)
    } catch (err) {
      setCalcError(extractErrorMessage(err))
    } finally {
      setCalculating(false)
    }
  }

  const CategoryForm = config.Form
  const yearly = period === '연 기준'
  const beforeAmount = result
    ? toManWon(yearly ? result.annual_before_amount : result.monthly_before_amount)
    : 0
  const afterAmount = result
    ? toManWon(yearly ? result.annual_after_amount : result.monthly_after_amount)
    : 0
  const savedAmount = result
    ? toManWon(yearly ? result.annual_savings_amount : result.monthly_savings_amount)
    : 0

  return (
    <section className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={() => navigate(`/policies/${policyId}`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 정책 상세로
      </button>

      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">혜택 계산기</p>
        <h1 className="mt-2 text-3xl font-black">예상 시뮬레이션</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          {policy.title}을(를) 받으면 생활비가 어떻게 달라지는지 한눈에 확인해보세요.
        </p>
      </div>

      <div className="mt-6 border-y border-gray-200 py-6">
        <h2 className="mb-4 text-lg font-bold">시뮬레이션 조건</h2>
        <CategoryForm values={formValues} onChange={updateFormValue} />
        <label className="mt-4 block max-w-xs text-sm font-semibold">
          지원 개월 수
          <input
            type="number"
            min={1}
            max={120}
            value={formValues.support_months ?? 12}
            onChange={(event) => updateFormValue('support_months', Number(event.target.value))}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          />
        </label>
        {calcError && <p className="mt-4 text-sm font-semibold text-rose-600">{calcError}</p>}
        <button
          type="button"
          onClick={() => void calculate()}
          disabled={calculating}
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3 font-bold text-white disabled:opacity-60"
        >
          {calculating ? '계산 중...' : '계산하기'} <ArrowRight size={16} />
        </button>
      </div>

      {result && (
        <>
          <div className="mt-6 inline-flex rounded-lg bg-slate-100 p-1">
            {(['월 기준', '연 기준'] as const).map((item) => (
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
              <p className="mt-6 border-t pt-5 text-sm text-gray-500">현재 기준</p>
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
      )}
    </section>
  )
}
