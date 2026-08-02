import { ArrowLeft, ArrowRight, TrendingDown } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ComponentType, FormEvent } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { extractErrorMessage } from '../../api/client'
import { getPolicy } from '../../api/policies'
import { simulatePolicyBenefit } from '../../api/simulator'
import CashVoucherSimulatorForm from '../../components/simulator/CashVoucherSimulatorForm'
import EmploymentEducationSimulatorForm from '../../components/simulator/EmploymentEducationSimulatorForm'
import HousingRentSimulatorForm from '../../components/simulator/HousingRentSimulatorForm'
import LoanInterestSimulatorForm from '../../components/simulator/LoanInterestSimulatorForm'
import SavingsAssetSimulatorForm from '../../components/simulator/SavingsAssetSimulatorForm'
import TaxDeductionSimulatorForm from '../../components/simulator/TaxDeductionSimulatorForm'
import type {
  CalcType,
  PolicyBenefitResponse,
  PolicyDetailResponse,
  SimulatorResult,
} from '../../types/api'
import type { SimulatorFormProps, SimulatorInputValue } from '../../types/simulator'
import { formatWon } from '../../utils/formatWon'
import { isPolicyDetailReturnNavigationState } from '../../utils/policyNavigation'

interface CalcTypeConfig {
  Form: ComponentType<SimulatorFormProps>
  label: string
}

const CALC_TYPE_CONFIG: Record<CalcType, CalcTypeConfig> = {
  LOAN_INTEREST: { Form: LoanInterestSimulatorForm, label: '대출 이자 지원' },
  SAVINGS_ASSET: { Form: SavingsAssetSimulatorForm, label: '자산형성 지원' },
  CASH_VOUCHER: { Form: CashVoucherSimulatorForm, label: '현금·바우처 지원' },
  HOUSING_RENT: { Form: HousingRentSimulatorForm, label: '주거비 지원' },
  EMPLOYMENT_EDUCATION: { Form: EmploymentEducationSimulatorForm, label: '고용·교육 지원' },
  TAX_DEDUCTION: { Form: TaxDeductionSimulatorForm, label: '세금 공제' },
}

function simulatableBenefits(policy: PolicyDetailResponse): PolicyBenefitResponse[] {
  // calc_type이 있어도 calculation_rule_json이 비어있으면(원문에서 확정 숫자를 못 뽑아
  // AI가 억지로 채우지 않은 경우) 계산이 불가능하다 - 백엔드가 이미 두 상태를 완전/null
  // 둘 중 하나로만 보장하므로(부분 채움 없음) null 여부만 확인하면 충분하다.
  return policy.benefits.filter(
    (benefit) => benefit.calc_type !== null && benefit.calculation_rule_json !== null,
  )
}

export default function Simulator() {
  const navigate = useNavigate()
  const location = useLocation()
  const { id } = useParams()
  const policyId = Number(id)
  const navigationState = isPolicyDetailReturnNavigationState(location.state)
    ? location.state
    : null
  const policyDetailReturnTo = navigationState?.policyDetailReturnTo ?? `/policies/${id}`

  const [policy, setPolicy] = useState<PolicyDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedBenefitId, setSelectedBenefitId] = useState<number | null>(null)
  const [period, setPeriod] = useState<'월 기준' | '연 기준'>('월 기준')
  const [formValues, setFormValues] = useState<Record<string, SimulatorInputValue | undefined>>({})
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
        const [firstBenefit] = simulatableBenefits(data)
        setSelectedBenefitId(firstBenefit?.id ?? null)
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

  const eligibleBenefits = useMemo(() => (policy ? simulatableBenefits(policy) : []), [policy])
  const selectedBenefit =
    eligibleBenefits.find((benefit) => benefit.id === selectedBenefitId) ?? null

  function selectBenefit(benefitId: number) {
    setSelectedBenefitId(benefitId)
    setFormValues({})
    setResult(null)
    setCalcError('')
  }

  function updateFormValue(name: string, value: SimulatorInputValue | undefined) {
    setFormValues((current) => ({ ...current, [name]: value }))
  }

  function returnToPolicyDetail() {
    navigate(policyDetailReturnTo, { state: navigationState?.policyDetailState })
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-gray-500">불러오는 중...</p>
  }
  if (error || !policy) {
    return (
      <section className="mx-auto max-w-4xl">
        <button
          onClick={returnToPolicyDetail}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
        >
          <ArrowLeft size={16} /> 정책 상세
        </button>
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error || '정책을 찾을 수 없습니다.'}
        </p>
      </section>
    )
  }

  if (!policy.is_simulatable || !selectedBenefit) {
    return (
      <section className="mx-auto max-w-4xl">
        <button
          onClick={returnToPolicyDetail}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
        >
          <ArrowLeft size={16} /> 정책 상세
        </button>
        <p className="mt-6 rounded-lg bg-slate-50 p-6 text-sm text-gray-600">
          이 정책은 아직 예상 시뮬레이션을 지원하지 않아요.
        </p>
      </section>
    )
  }

  const config = CALC_TYPE_CONFIG[selectedBenefit.calc_type as CalcType]
  const rule = (selectedBenefit.calculation_rule_json ?? {}) as Record<string, unknown>

  async function calculate() {
    if (!selectedBenefit) return
    setCalculating(true)
    setCalcError('')
    try {
      const data = await simulatePolicyBenefit(policyId, selectedBenefit.id, {
        user_input: formValues as Record<string, number>,
      })
      setResult(data)
    } catch (err) {
      setCalcError(extractErrorMessage(err))
    } finally {
      setCalculating(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void calculate()
  }

  const CategoryForm = config.Form
  const yearly = period === '연 기준'
  const beforeAmount = result
    ? yearly
      ? result.annual_before_amount
      : result.monthly_before_amount
    : 0
  const afterAmount = result
    ? yearly
      ? result.annual_after_amount
      : result.monthly_after_amount
    : 0
  const savedAmount = result
    ? yearly
      ? result.annual_savings_amount
      : result.monthly_savings_amount
    : 0

  return (
    <section className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={returnToPolicyDetail}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 정책 상세
      </button>

      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">혜택 계산기</p>
        <h1 className="mt-2 text-3xl font-black">예상 시뮬레이션</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          {policy.title}을(를) 받으면 생활비가 어떻게 달라지는지 한눈에 확인해보세요.
        </p>
      </div>

      {eligibleBenefits.length > 1 && (
        <label className="mt-5 block max-w-sm text-sm font-semibold">
          계산할 혜택 선택
          <select
            value={selectedBenefit.id}
            onChange={(event) => selectBenefit(Number(event.target.value))}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-normal"
          >
            {eligibleBenefits.map((benefit) => (
              <option key={benefit.id} value={benefit.id}>
                {benefit.display_text ?? CALC_TYPE_CONFIG[benefit.calc_type as CalcType].label}
              </option>
            ))}
          </select>
        </label>
      )}

      <form className="mt-6 border-y border-gray-200 py-6" onSubmit={handleSubmit}>
        <h2 className="mb-4 text-lg font-bold">{config.label} 시뮬레이션 조건</h2>
        <CategoryForm
          key={selectedBenefit.id}
          rule={rule}
          values={formValues}
          onChange={updateFormValue}
        />
        {calcError && <p className="mt-4 text-sm font-semibold text-rose-600">{calcError}</p>}
        <button
          type="submit"
          disabled={calculating}
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3 font-bold text-white disabled:opacity-60"
        >
          {calculating ? '계산 중...' : '계산하기'} <ArrowRight size={16} />
        </button>
      </form>

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
              <p className="mt-5 text-4xl font-black">{formatWon(beforeAmount)}</p>
              <p className="mt-6 border-t pt-5 text-sm text-gray-500">현재 기준</p>
            </div>
            <div className="grid place-items-center">
              <ArrowRight className="rotate-90 text-blue-600 md:rotate-0" />
            </div>
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
              <p className="text-sm font-semibold text-blue-700">지원 후 · After</p>
              <p className="mt-5 text-4xl font-black text-blue-700">{formatWon(afterAmount)}</p>
              <p className="mt-6 border-t border-blue-200 pt-5 text-sm text-blue-700">
                지원금 반영 후 예상 금액
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-col items-center rounded-xl border border-blue-200 bg-white p-6 text-center">
            <TrendingDown className="text-blue-600" />
            <p className="mt-3 text-sm text-gray-500">{period} 총 절감 금액</p>
            <p className="mt-1 text-3xl font-black text-blue-600">+{formatWon(savedAmount)}</p>
          </div>

          <p className="mt-4 rounded-lg bg-slate-50 p-4 text-xs leading-6 text-gray-500">
            {result.disclaimer}
          </p>
        </>
      )}
    </section>
  )
}
