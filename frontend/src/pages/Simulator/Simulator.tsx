import { ArrowLeft, ArrowRight, TrendingDown, TrendingUp } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ComponentType, FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
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

// 각 calc_type의 계산 함수가 고정으로 갖는 방향성(services/policy_engine/simulator.py의
// calculate_*() direction 파라미터, API 응답엔 노출되지 않음)을 프론트에서 그대로 재현한다.
// 정책/benefit별로 달라지지 않고 calc_type 1개당 고정값이라 여기서 하드코딩해도 안전하다.
const REDUCE_CALC_TYPES: ReadonlySet<CalcType> = new Set([
  'LOAN_INTEREST',
  'HOUSING_RENT',
  'TAX_DEDUCTION',
])

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
  const { id } = useParams()
  const policyId = Number(id)

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
  const hasUnsimulatedBenefits = policy != null && policy.benefits.length > eligibleBenefits.length

  function selectBenefit(benefitId: number) {
    setSelectedBenefitId(benefitId)
    setFormValues({})
    setResult(null)
    setCalcError('')
  }

  function updateFormValue(name: string, value: SimulatorInputValue | undefined) {
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
          onClick={() => navigate(`/policies/${policyId}`)}
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
  // 훈련수당/교육비 없이 취업성공수당 같은 1회성 혜택만 있으면 월/연 절감액이 항상 0이라,
  // "총 절감 금액 +0원"만 보고 혜택이 없다고 오해하기 쉽다 - 이 경우 총 예상 혜택 카드를
  // 상단으로 올리고 1회성 지급임을 배지로 알린다.
  const isOneTimeOnlyBenefit =
    result != null &&
    result.category === 'EMPLOYMENT_EDUCATION' &&
    Number(result.monthly_savings_amount) === 0 &&
    Number(result.total_benefit_amount) > 0
  const isReduceDirection = result != null && REDUCE_CALC_TYPES.has(result.category)
  // support_months가 12 미만이면 연 기준 금액이 월×12가 아니라 실제 지원 개월만큼만
  // 반영되므로(_build_result의 active_months_in_year), 오해를 막기 위해 안내 문구를 띄운다.
  const isPartialYearSupport =
    result != null &&
    result.category === 'EMPLOYMENT_EDUCATION' &&
    !isOneTimeOnlyBenefit &&
    result.support_months < 12
  // 취업성공수당처럼 1회성 성분이 합산된 결과에만 "(1회성 포함 총액)" 부제를 붙인다 -
  // calculate_employment_education()이 이 값을 0으로 채워 넣더라도 breakdown엔 항상
  // employment_success_bonus_amount 키가 있으므로 존재 여부가 아니라 값(> 0)으로 판별한다.
  const includesOneTimeComponent =
    result != null &&
    result.category === 'EMPLOYMENT_EDUCATION' &&
    Number(result.breakdown.employment_success_bonus_amount ?? 0) > 0
  const totalBenefitLabel = `내 조건 기준 예상 혜택${includesOneTimeComponent ? ' (1회성 포함 총액)' : ''}`

  return (
    <section className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={() => navigate(`/policies/${policyId}`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 정책 상세
      </button>

      <div className="mt-5">
        <h1 className="text-3xl font-black">예상 시뮬레이션</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          {policy.title} 혜택을 받으면 생활비가 어떻게 달라지는지 한눈에 확인해보세요.
        </p>
      </div>

      {hasUnsimulatedBenefits && (
        <p className="mt-5 rounded-lg bg-slate-50 p-4 text-xs leading-6 text-gray-500">
          이 정책에는 혜택 항목이 총 {policy.benefits.length}개 있어요. 그중 {eligibleBenefits.length}
          개만 지금 시뮬레이션에 반영돼요. 정책 카드의 최대 예상 혜택
          {policy.estimated_benefit_amount != null
            ? `(${formatWon(policy.estimated_benefit_amount)})`
            : ''}
          은 전체 항목 기준이라 이 결과보다 클 수 있어요.
        </p>
      )}

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
          {isOneTimeOnlyBenefit ? (
            <>
              <div className="mt-6 flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 text-center">
                <p className="text-sm text-gray-500">{totalBenefitLabel}</p>
                <p className="mt-1 text-2xl font-black">{formatWon(result.total_benefit_amount)}</p>
              </div>
              <p className="mt-4 text-center text-sm text-gray-500">
                이 정책은 매월 반복 지급이 아닌, 조건 충족 시 1회성으로 지급되는 수당이에요.
              </p>
            </>
          ) : (
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

              {isPartialYearSupport && (
                <div className="mt-4">
                  <span className="inline-block rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600">
                    이 혜택은 {result.support_months}개월간 지급돼요.
                  </span>
                </div>
              )}

              <div className="mt-5 grid items-stretch gap-4 md:grid-cols-[1fr_auto_1fr]">
                <div className="rounded-xl border border-gray-200 bg-white p-6">
                  <p className="text-sm font-semibold text-gray-500">
                    지원 전 ({isReduceDirection ? '기존 지출' : '기존 수령액'})
                  </p>
                  <p className="mt-5 text-4xl font-black">{formatWon(beforeAmount)}</p>
                  <p className="mt-6 border-t pt-5 text-sm text-gray-500">현재 기준</p>
                </div>
                <div className="grid place-items-center">
                  <ArrowRight className="rotate-90 text-blue-600 md:rotate-0" />
                </div>
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-6">
                  <p className="text-sm font-semibold text-blue-700">
                    지원 후 ({isReduceDirection ? '예상 지출' : '예상 수령액'})
                  </p>
                  <p className="mt-5 text-4xl font-black text-blue-700">{formatWon(afterAmount)}</p>
                  <p className="mt-6 border-t border-blue-200 pt-5 text-sm text-blue-700">
                    지원금 반영 후 예상 금액
                  </p>
                </div>
              </div>

              <div className="mt-5 flex flex-col items-center rounded-xl border border-blue-200 bg-white p-6 text-center">
                {isReduceDirection ? (
                  <TrendingDown className="text-blue-600" />
                ) : (
                  <TrendingUp className="text-blue-600" />
                )}
                <p className="mt-3 text-sm text-gray-500">
                  {period} {isReduceDirection ? '총 절감 금액' : '총 지원 증가액'}
                </p>
                <p className="mt-1 text-3xl font-black text-blue-600">+{formatWon(savedAmount)}</p>
              </div>

              <div className="mt-5 flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 text-center">
                <p className="text-sm text-gray-500">{totalBenefitLabel}</p>
                <p className="mt-1 text-2xl font-black">{formatWon(result.total_benefit_amount)}</p>
              </div>
            </>
          )}

          {result.category === 'SAVINGS_ASSET' && (
            <p className="mt-4 rounded-lg bg-slate-50 p-4 text-xs leading-6 text-gray-500">
              ※ 만기 이자는 금리(%)로 안내되며, 실제 이자 금액은 세부 약정 조건에 따라 달라집니다.
            </p>
          )}

          <p className="mt-4 rounded-lg bg-slate-50 p-4 text-xs leading-6 text-gray-500">
            {result.disclaimer}
          </p>
        </>
      )}
    </section>
  )
}
