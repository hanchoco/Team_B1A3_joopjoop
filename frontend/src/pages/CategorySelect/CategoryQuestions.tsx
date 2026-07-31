import { ArrowLeft, ArrowRight, CheckCircle2, ChevronDown, Clock3, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { listCategories, listCategoryQuestions, saveCategoryAnswers } from '../../api/categories'
import { extractErrorMessage } from '../../api/client'
import type { CategoryAnswerUpsert, CategoryQuestionResponse } from '../../types/api'

interface SelectOption {
  label: string
  value: string
}

function parseOptions(optionsJson: unknown): SelectOption[] {
  if (!Array.isArray(optionsJson)) return []

  return optionsJson.flatMap((item) => {
    if (typeof item === 'string') {
      return [{ label: item, value: item }]
    }
    if (
      item &&
      typeof item === 'object' &&
      typeof (item as { label?: unknown }).label === 'string' &&
      typeof (item as { value?: unknown }).value === 'string'
    ) {
      return [
        {
          label: (item as { label: string }).label,
          value: (item as { value: string }).value,
        },
      ]
    }
    return []
  })
}

function removeDuplicateCompanySizeQuestions(
  questions: CategoryQuestionResponse[],
): CategoryQuestionResponse[] {
  const companySizeQuestions = questions.filter(
    (item) =>
      item.question_key.includes('company_size') ||
      (item.label.includes('회사') && item.label.includes('규모')),
  )
  if (companySizeQuestions.length < 2) return questions

  const detailedQuestion = companySizeQuestions.at(-1)
  return questions.filter(
    (item) => !companySizeQuestions.includes(item) || item.id === detailedQuestion?.id,
  )
}

function isRepeatedEmploymentStatusQuestion(question: CategoryQuestionResponse): boolean {
  if (question.question_key === 'employment.contract_type_code') return false

  return (
    question.question_key.includes('employment_status') ||
    question.label.includes('고용 형태') ||
    question.label.includes('취업 상태') ||
    question.label.includes('취업상태') ||
    question.label.includes('경제활동 상태')
  )
}

function policiesLinkFor(categoryName: string, answersUpdated = false): string {
  const params = new URLSearchParams(categoryName ? { category: categoryName } : {})
  if (answersUpdated) params.set('answers', 'updated')
  return `/policies?${params.toString()}`
}

interface AmountRange {
  label: string
  min: number
  max: number | null
  representativeValue: number
}

interface AssetBreakdown {
  housingDeposit?: number
  carValue?: number
  debt?: number
  savings?: number
  generalAssets?: number
}

const ASSET_BREAKDOWN_FIELDS: {
  key: keyof AssetBreakdown
  label: string
  hint: string
  optional?: boolean
}[] = [
  {
    key: 'housingDeposit',
    label: '현재 거주 중인 집의 보증금은 얼마인가요?',
    hint: '보유 자산 중 가장 큰 금액을 적어주세요.',
  },
  {
    key: 'carValue',
    label: '보유한 자동차가 있다면 현재 차량 가격은 얼마인가요?',
    hint: '자동차가 없다면 비워두거나 0원을 입력해주세요.',
    optional: true,
  },
  {
    key: 'savings',
    label: '예적금이나 주식 등 모아둔 돈은 대략 얼마인가요?',
    hint: '현재 보유한 금융자산의 대략적인 금액을 적어주세요.',
  },
  {
    key: 'generalAssets',
    label: '그 밖에 보유한 일반자산은 대략 얼마인가요?',
    hint: '토지, 상가, 귀금속 등 그 밖의 자산이 없다면 비워두거나 0원을 입력해주세요.',
    optional: true,
  },
  {
    key: 'debt',
    label: '학자금 대출이나 전·월세 대출이 있나요?',
    hint: '현재 남아 있는 대출 원금을 적어주세요. 없다면 0원을 입력해주세요.',
  },
]

const AMOUNT_RANGES: Record<string, AmountRange[]> = {
  'housing.deposit_amount': [
    { label: '1천만원 미만', min: 0, max: 10_000_000, representativeValue: 5_000_000 },
    { label: '1천만~3천만원', min: 10_000_000, max: 30_000_000, representativeValue: 20_000_000 },
    { label: '3천만~5천만원', min: 30_000_000, max: 50_000_000, representativeValue: 40_000_000 },
    { label: '5천만~1억원', min: 50_000_000, max: 100_000_000, representativeValue: 75_000_000 },
    { label: '1억원 이상', min: 100_000_000, max: null, representativeValue: 100_000_000 },
  ],
  'housing.monthly_rent_amount': [
    { label: '30만원 미만', min: 0, max: 300_000, representativeValue: 150_000 },
    { label: '30만~50만원', min: 300_000, max: 500_000, representativeValue: 400_000 },
    { label: '50만~70만원', min: 500_000, max: 700_000, representativeValue: 600_000 },
    { label: '70만~100만원', min: 700_000, max: 1_000_000, representativeValue: 850_000 },
    { label: '100만원 이상', min: 1_000_000, max: null, representativeValue: 1_000_000 },
  ],
  'finance.monthly_income_amount': [
    { label: '100만원 미만', min: 0, max: 1_000_000, representativeValue: 500_000 },
    { label: '100만~200만원', min: 1_000_000, max: 2_000_000, representativeValue: 1_500_000 },
    { label: '200만~300만원', min: 2_000_000, max: 3_000_000, representativeValue: 2_500_000 },
    { label: '300만~400만원', min: 3_000_000, max: 4_000_000, representativeValue: 3_500_000 },
    { label: '400만원 이상', min: 4_000_000, max: null, representativeValue: 4_000_000 },
  ],
  'finance.annual_income_amount': [
    { label: '1,200만원 미만', min: 0, max: 12_000_000, representativeValue: 6_000_000 },
    {
      label: '1,200만~2,400만원',
      min: 12_000_000,
      max: 24_000_000,
      representativeValue: 18_000_000,
    },
    {
      label: '2,400만~3,600만원',
      min: 24_000_000,
      max: 36_000_000,
      representativeValue: 30_000_000,
    },
    {
      label: '3,600만~4,800만원',
      min: 36_000_000,
      max: 48_000_000,
      representativeValue: 42_000_000,
    },
    {
      label: '4,800만원 이상',
      min: 48_000_000,
      max: null,
      representativeValue: 48_000_000,
    },
  ],
  'finance.fixed_monthly_expense_amount': [
    { label: '50만원 미만', min: 0, max: 500_000, representativeValue: 250_000 },
    { label: '50만~100만원', min: 500_000, max: 1_000_000, representativeValue: 750_000 },
    {
      label: '100만~200만원',
      min: 1_000_000,
      max: 2_000_000,
      representativeValue: 1_500_000,
    },
    {
      label: '200만~300만원',
      min: 2_000_000,
      max: 3_000_000,
      representativeValue: 2_500_000,
    },
    {
      label: '300만원 이상',
      min: 3_000_000,
      max: null,
      representativeValue: 3_000_000,
    },
  ],
}

const RESIDENCE_MONTH_OPTIONS = Array.from({ length: 240 }, (_, index) => index + 1)
const HIDDEN_QUESTION_KEYS = new Set(['finance.total_debt_amount'])
const COMPANY_SIZE_LABELS: Record<string, string> = {
  MICRO: '1~4인 (5인 미만)',
  SMALL: '5~49인',
  MEDIUM: '50~299인',
  LARGE: '300인 이상',
  PUBLIC: '공공기관·공기업',
  UNKNOWN: '현재 근무 중이 아님',
}
const CONTRACT_TYPE_LABELS: Record<string, string> = {
  PERMANENT: '정규직 (계약기간을 정하지 않음)',
  FIXED_TERM: '계약직·기간제·인턴 (계약 종료일이 있음)',
  DISPATCHED: '파견직·용역직 (소속 회사와 근무지가 다름)',
  FREELANCER: '프리랜서·특수고용',
  DAILY: '일용직·단기 아르바이트',
  UNKNOWN: '현재 근무 중이 아님',
}
const QUICK_AMOUNT_OPTIONS = [
  { label: '+10만', value: 100_000 },
  { label: '+100만', value: 1_000_000 },
  { label: '+1,000만', value: 10_000_000 },
]

function formatAmountInput(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.trunc(value).toLocaleString('ko-KR')
    : ''
}

function formatKoreanWon(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return ''

  const amount = Math.max(0, Math.trunc(value))
  if (amount === 0) return '0원'

  const eok = Math.floor(amount / 100_000_000)
  const man = Math.floor((amount % 100_000_000) / 10_000)
  const won = amount % 10_000
  const parts: string[] = []

  if (eok > 0) parts.push(`${eok.toLocaleString('ko-KR')}억`)
  if (man > 0) parts.push(`${man.toLocaleString('ko-KR')}만`)
  if (won > 0) parts.push(`${won.toLocaleString('ko-KR')}원`)
  else parts.push('원')

  return parts.join(' ')
}

export default function CategoryQuestions() {
  const { categoryId: categoryIdParam } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const categoryId = Number(categoryIdParam)
  const isFromHome = searchParams.get('from') === 'home'
  const previousPath = isFromHome ? '/' : '/categories'
  const previousLabel = '돌아가기'

  const [categoryName, setCategoryName] = useState('')
  const [categoryCode, setCategoryCode] = useState('')
  const [questions, setQuestions] = useState<CategoryQuestionResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<number, unknown>>({})
  const [monthListOpen, setMonthListOpen] = useState(false)
  const [assetBreakdown, setAssetBreakdown] = useState<AssetBreakdown>({})

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        if (!Number.isFinite(categoryId)) {
          throw new Error('올바르지 않은 카테고리입니다.')
        }
        setLoading(true)
        setError('')
        return Promise.all([listCategories(), listCategoryQuestions(categoryId)])
      })
      .then((result) => {
        if (cancelled || !result) return
        const [categories, categoryQuestions] = result
        const category = categories.find((item) => item.id === categoryId)
        setCategoryName(category?.name ?? '')
        setCategoryCode(category?.code ?? '')
        if (categoryQuestions.length === 0) {
          navigate(policiesLinkFor(category?.name ?? ''), { replace: true })
          return
        }
        setQuestions(categoryQuestions)
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
  }, [categoryId, navigate])

  function setAnswerValue(questionId: number, value: unknown) {
    setAnswers((current) => {
      if (value === undefined) {
        const nextAnswers = { ...current }
        delete nextAnswers[questionId]
        return nextAnswers
      }
      return { ...current, [questionId]: value }
    })
  }

  function toggleMultiSelectAnswer(questionId: number, optionValue: string) {
    setAnswers((current) => {
      const selectedValues = Array.isArray(current[questionId])
        ? (current[questionId] as unknown[]).filter(
            (value): value is string => typeof value === 'string',
          )
        : []
      const nextValues = selectedValues.includes(optionValue)
        ? selectedValues.filter((value) => value !== optionValue)
        : [...selectedValues, optionValue]

      if (nextValues.length === 0) {
        const nextAnswers = { ...current }
        delete nextAnswers[questionId]
        return nextAnswers
      }
      return { ...current, [questionId]: nextValues }
    })
  }

  function setAssetBreakdownValue(
    questionId: number,
    key: keyof AssetBreakdown,
    value: number | undefined,
  ) {
    const nextBreakdown = { ...assetBreakdown, [key]: value }
    setAssetBreakdown(nextBreakdown)

    const { housingDeposit, carValue, debt, savings, generalAssets } = nextBreakdown
    const debtQuestion = questions.find((item) => item.question_key === 'finance.total_debt_amount')
    if (debtQuestion) {
      setAnswerValue(debtQuestion.id, debt)
    }

    if (
      typeof housingDeposit === 'number' &&
      typeof debt === 'number' &&
      typeof savings === 'number'
    ) {
      setAnswerValue(
        questionId,
        Math.max(0, housingDeposit + (carValue ?? 0) + savings + (generalAssets ?? 0) - debt),
      )
    } else {
      setAnswerValue(questionId, undefined)
    }
  }

  async function finish(answerValues: Record<number, unknown> = answers) {
    setSubmitting(true)
    setError('')
    try {
      const payload: CategoryAnswerUpsert[] = questions
        .filter((item) => item.id in answerValues)
        .map((item) => ({
          question_id: item.id,
          answer_json: { value: answerValues[item.id] },
        }))
      if (payload.length > 0) {
        await saveCategoryAnswers(categoryId, payload)
      }
      navigate(policiesLinkFor(categoryName, true))
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  function skipQuestion(questionId: number, isLast: boolean) {
    const nextAnswers = { ...answers, [questionId]: null }
    setAnswers(nextAnswers)
    setMonthListOpen(false)
    if (isLast) {
      void finish(nextAnswers)
    } else {
      setStep((current) => current + 1)
    }
  }

  function goToNextQuestion() {
    setMonthListOpen(false)

    if (isContractTypeQuestion && answers[question.id] === 'UNKNOWN') {
      const nextAnswers = { ...answers }
      visibleQuestions.slice(step + 1).forEach((item) => {
        nextAnswers[item.id] = null
      })
      setAnswers(nextAnswers)
      void finish(nextAnswers)
      return
    }

    setStep((current) => current + 1)
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-gray-500">불러오는 중...</p>
  }

  if (error && questions.length === 0) {
    return (
      <section className="mx-auto max-w-3xl">
        <button
          type="button"
          onClick={() => navigate(previousPath)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
        >
          <ArrowLeft size={16} /> {previousLabel}
        </button>
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      </section>
    )
  }

  if (questions.length === 0) return null

  const visibleQuestions = removeDuplicateCompanySizeQuestions(
    questions.filter(
      (item) =>
        !HIDDEN_QUESTION_KEYS.has(item.question_key) &&
        !(categoryCode === 'EMPLOYMENT' && isRepeatedEmploymentStatusQuestion(item)),
    ),
  )
  const question = visibleQuestions[step]
  const remaining = visibleQuestions.length - step - 1
  const isLast = step === visibleQuestions.length - 1
  const answered = question.id in answers
  const isHousing = categoryCode === 'HOUSING'
  const canSkipQuestion = isHousing || categoryCode === 'FINANCE' || categoryCode === 'EMPLOYMENT'
  const isHomeOwnershipQuestion = question.question_key === 'housing.home_ownership_status_code'
  const amountRanges = AMOUNT_RANGES[question.question_key]
  const isMonthDurationQuestion =
    question.question_key === 'housing.residence_months' ||
    question.question_key === 'employment.tenure_months'
  const isAnnualIncome = question.question_key === 'finance.annual_income_amount'
  const isTotalAssetQuestion = question.question_key === 'finance.total_asset_amount'
  const isCompanySizeQuestion = question.question_key === 'employment.company_size_code'
  const isContractTypeQuestion = question.question_key === 'employment.contract_type_code'
  const monthlyIncomeQuestion = questions.find(
    (item) => item.question_key === 'finance.monthly_income_amount',
  )
  const monthlyIncomeAnswer = monthlyIncomeQuestion ? answers[monthlyIncomeQuestion.id] : undefined
  const annualIncomeExample =
    typeof monthlyIncomeAnswer === 'number' ? monthlyIncomeAnswer * 12 : null

  return (
    <section className="mx-auto max-w-3xl">
      <button
        type="button"
        onClick={() => {
          setMonthListOpen(false)
          navigate(previousPath)
        }}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> {previousLabel}
      </button>

      <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 px-5 py-4">
        <div className="flex items-center gap-3">
          <Clock3 size={19} className="text-blue-600" />
          <div>
            <p className="text-sm font-bold text-blue-800">
              앞으로 {remaining}개의 질문이 남았어요
            </p>
            <p className="mt-1 text-xs text-gray-600">
              답변은 {categoryName} 정책의 추천 정확도를 높이는 데만 사용해요.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 flex gap-2">
        {visibleQuestions.map((item, index) => (
          <span
            key={item.id}
            className={`h-1.5 flex-1 rounded-full ${index <= step ? 'bg-blue-600' : 'bg-gray-200'}`}
          />
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-gray-200 bg-white p-6 sm:p-10">
        <p className="text-sm font-bold text-blue-600">
          {categoryName} 추가 질문 · {step + 1}/{visibleQuestions.length}
        </p>
        <h1 className="mt-4 text-2xl font-black sm:text-3xl">{question.label}</h1>
        {question.description && (
          <p className="mt-2 text-sm text-gray-500">{question.description}</p>
        )}
        {isTotalAssetQuestion && (
          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm leading-6 text-gray-700">
              총자산가액은 보유한 부동산, 자동차, 금융자산과 일반자산을 모두 합한 뒤 부채를 뺀
              금액이에요.
            </p>
            <p className="mt-2 text-sm font-bold text-blue-800">
              총자산가액 = (부동산 + 자동차 + 금융자산 + 일반자산) - 부채
            </p>
            <p className="mt-2 text-xs leading-5 text-gray-500">
              여기서는 간편 확인을 위해 주요 항목인 보증금과 모아둔 돈에서 대출금을 빼서 예상 금액을
              계산해요.
            </p>
          </div>
        )}
        {isCompanySizeQuestion && (
          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm font-bold text-blue-800">
              회사 전체의 상시근로자 수로 선택해주세요.
            </p>
            <p className="mt-1 text-xs leading-5 text-gray-600">
              소속 팀이나 지점 인원이 아니라 본사와 지점을 포함한 회사 전체 인원이 기준입니다.
              공공기관·공기업이라면 인원수와 관계없이 해당 선택지를 눌러주세요.
            </p>
          </div>
        )}
        {isContractTypeQuestion && (
          <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm font-bold text-blue-800">
              근로계약서에 적힌 계약기간과 고용 방식을 기준으로 선택해주세요.
            </p>
            <p className="mt-1 text-xs leading-5 text-gray-600">
              계약 종료일이 정해져 있다면 계약직·기간제를, 다른 회사에 소속되어 현재 근무지로
              파견됐다면 파견직·용역직을 선택하면 됩니다.
            </p>
          </div>
        )}

        <div className="mt-8">
          {question.answer_type === 'BOOLEAN' || isHomeOwnershipQuestion ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {(isHomeOwnershipQuestion
                ? [
                    { label: '예', value: 'SELF' },
                    { label: '아니오', value: 'NONE' },
                  ]
                : [
                    { label: '예', value: true },
                    { label: '아니요', value: false },
                  ]
              ).map((option) => {
                const selected = answers[question.id] === option.value
                return (
                  <button
                    key={option.label}
                    type="button"
                    onClick={() => setAnswerValue(question.id, option.value)}
                    className={`flex min-h-16 items-center justify-between rounded-lg border px-5 py-4 text-left text-sm font-semibold transition ${selected ? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-100' : 'border-gray-200 hover:border-blue-300'}`}
                  >
                    {option.label}
                    {selected && <CheckCircle2 size={18} />}
                  </button>
                )
              })}
            </div>
          ) : isTotalAssetQuestion ? (
            <div className="space-y-5">
              {ASSET_BREAKDOWN_FIELDS.map((field) => {
                const value = assetBreakdown[field.key]
                return (
                  <label key={field.key} className="block text-sm font-semibold">
                    {field.label}
                    <span className="mt-1 block text-xs font-normal text-gray-500">
                      {field.hint}
                    </span>
                    <input
                      type="text"
                      inputMode="numeric"
                      required={!field.optional}
                      value={formatAmountInput(value)}
                      onChange={(event) => {
                        const digits = event.target.value.replace(/\D/g, '')
                        setAssetBreakdownValue(
                          question.id,
                          field.key,
                          digits === '' ? undefined : Number(digits),
                        )
                      }}
                      placeholder="예: 20,000,000"
                      className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    />
                    {typeof value === 'number' && (
                      <span className="mt-2 block px-4 text-xs font-medium text-gray-400">
                        {formatKoreanWon(value)}
                      </span>
                    )}
                  </label>
                )
              })}
              {typeof answers[question.id] === 'number' && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                  <p className="text-xs font-semibold text-emerald-700">
                    보증금 + 자동차 + 모아둔 돈 + 일반자산 - 대출금
                  </p>
                  <p className="mt-1 text-lg font-black text-emerald-800">
                    예상 총자산가액 {formatKoreanWon(answers[question.id])}
                  </p>
                </div>
              )}
            </div>
          ) : question.answer_type === 'NUMBER' ? (
            <div className="block text-sm font-semibold">
              <label htmlFor={`question-${question.id}`}>
                숫자로 입력해주세요{question.unit ? ` (${question.unit})` : ''}
              </label>
              <div className="relative mt-2">
                <input
                  id={`question-${question.id}`}
                  type={amountRanges ? 'text' : 'number'}
                  inputMode={amountRanges ? 'numeric' : undefined}
                  min={!amountRanges && (isHousing || isMonthDurationQuestion) ? 0 : undefined}
                  value={
                    amountRanges
                      ? formatAmountInput(answers[question.id])
                      : typeof answers[question.id] === 'number'
                        ? (answers[question.id] as number)
                        : ''
                  }
                  onChange={(event) => {
                    if (amountRanges) {
                      const digits = event.target.value.replace(/\D/g, '')
                      setAnswerValue(question.id, digits === '' ? undefined : Number(digits))
                    } else {
                      const value = event.target.value
                      setAnswerValue(
                        question.id,
                        value === ''
                          ? undefined
                          : Math.max(
                              isHousing || isMonthDurationQuestion ? 0 : -Infinity,
                              Number(value),
                            ),
                      )
                    }
                  }}
                  placeholder={
                    isAnnualIncome
                      ? annualIncomeExample === null
                        ? '예: 월평균 소득 × 12'
                        : `예: ${formatAmountInput(annualIncomeExample)} (월평균 × 12)`
                      : amountRanges
                        ? '예: 100,000,000'
                        : isMonthDurationQuestion
                          ? '개월 수 입력'
                          : undefined
                  }
                  className={`w-full rounded-lg border border-gray-300 px-4 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 ${
                    amountRanges
                      ? 'py-3.5 pr-12'
                      : isMonthDurationQuestion
                        ? 'py-3.5 pr-12 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none'
                        : 'py-3.5'
                  }`}
                />
                {amountRanges && typeof answers[question.id] === 'number' && (
                  <button
                    type="button"
                    onClick={() => setAnswerValue(question.id, undefined)}
                    className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-full text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
                    aria-label="입력한 금액 지우기"
                  >
                    <X size={16} />
                  </button>
                )}
                {isMonthDurationQuestion && (
                  <>
                    <button
                      type="button"
                      onClick={() => setMonthListOpen((current) => !current)}
                      className="absolute right-0 top-0 grid h-full w-12 place-items-center text-gray-500"
                      aria-label="개월 수 목록 열기"
                      aria-expanded={monthListOpen}
                    >
                      <ChevronDown
                        size={19}
                        className={`transition ${monthListOpen ? 'rotate-180' : ''}`}
                      />
                    </button>
                    {monthListOpen && (
                      <div className="absolute z-20 mt-2 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white p-1 shadow-lg">
                        {RESIDENCE_MONTH_OPTIONS.map((month) => {
                          const selected = answers[question.id] === month
                          return (
                            <button
                              key={month}
                              type="button"
                              onClick={() => {
                                setAnswerValue(question.id, month)
                                setMonthListOpen(false)
                              }}
                              className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-normal ${
                                selected
                                  ? 'bg-blue-50 font-bold text-blue-700'
                                  : 'text-gray-700 hover:bg-slate-50'
                              }`}
                            >
                              {month}개월
                              {selected && <CheckCircle2 size={16} />}
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
              {amountRanges && typeof answers[question.id] === 'number' && (
                <span
                  className="mt-2 block px-4 text-xs font-medium text-gray-400"
                  aria-live="polite"
                >
                  {formatKoreanWon(answers[question.id])}
                </span>
              )}
              {amountRanges && (
                <>
                  <span className="mt-4 grid grid-cols-3 gap-2">
                    {QUICK_AMOUNT_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => {
                          const answer = answers[question.id]
                          const currentAmount = typeof answer === 'number' ? answer : 0
                          setAnswerValue(question.id, currentAmount + option.value)
                        }}
                        className="rounded-lg border border-blue-200 bg-blue-50 px-2 py-2.5 text-sm font-bold text-blue-700 transition hover:border-blue-400 hover:bg-blue-100"
                      >
                        {option.label}
                      </button>
                    ))}
                  </span>
                  <span className="mt-5 block text-sm font-bold text-gray-700">또는 구간 선택</span>
                  <span className="mt-1 block text-xs font-normal text-gray-500">
                    구간을 선택하면 대표 금액이 입력돼요. 정확한 금액을 알면 직접 수정할 수 있어요.
                  </span>
                  <span className="mt-3 grid gap-2 sm:grid-cols-2">
                    {amountRanges.map((range) => {
                      const answer = answers[question.id]
                      const selected =
                        typeof answer === 'number' &&
                        answer >= range.min &&
                        (range.max === null || answer < range.max)
                      return (
                        <button
                          key={range.label}
                          type="button"
                          onClick={() => setAnswerValue(question.id, range.representativeValue)}
                          className={`rounded-lg border px-4 py-3 text-left text-sm font-semibold transition ${
                            selected
                              ? 'border-blue-600 bg-blue-50 text-blue-700'
                              : 'border-gray-200 bg-white hover:border-blue-300'
                          }`}
                        >
                          {range.label}
                        </button>
                      )
                    })}
                  </span>
                </>
              )}
            </div>
          ) : parseOptions(question.options_json).length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {parseOptions(question.options_json).map((option) => {
                const selected =
                  question.answer_type === 'MULTI_SELECT'
                    ? Array.isArray(answers[question.id]) &&
                      (answers[question.id] as unknown[]).includes(option.value)
                    : answers[question.id] === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    disabled={submitting}
                    onClick={() =>
                      question.answer_type === 'MULTI_SELECT'
                        ? toggleMultiSelectAnswer(question.id, option.value)
                        : setAnswerValue(question.id, option.value)
                    }
                    className={`flex min-h-16 items-center justify-between rounded-lg border px-5 py-4 text-left text-sm font-semibold transition ${selected ? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-100' : 'border-gray-200 hover:border-blue-300'}`}
                  >
                    {isCompanySizeQuestion
                      ? (COMPANY_SIZE_LABELS[option.value] ?? option.label)
                      : isContractTypeQuestion
                        ? (CONTRACT_TYPE_LABELS[option.value] ?? option.label)
                        : option.label}
                    {selected && <CheckCircle2 size={18} />}
                  </button>
                )
              })}
            </div>
          ) : (
            <label className="block text-sm font-semibold">
              답변을 입력해주세요
              <input
                type="text"
                value={
                  typeof answers[question.id] === 'string' ? (answers[question.id] as string) : ''
                }
                onChange={(event) => setAnswerValue(question.id, event.target.value)}
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </label>
          )}
        </div>

        {error && <p className="mt-4 text-sm font-semibold text-rose-600">{error}</p>}

        <div className={`mt-8 grid gap-3 ${canSkipQuestion ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
          <button
            type="button"
            disabled={step === 0 || submitting}
            onClick={() => {
              setMonthListOpen(false)
              setStep((current) => current - 1)
            }}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 px-5 py-3.5 font-bold text-gray-600 transition hover:border-gray-400 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowLeft size={18} /> 이전 질문
          </button>
          {canSkipQuestion && (
            <button
              type="button"
              disabled={submitting}
              onClick={() => skipQuestion(question.id, isLast)}
              className="inline-flex w-full items-center justify-center rounded-lg border border-gray-300 px-5 py-3.5 font-bold text-gray-600 transition hover:border-gray-400 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              잘 모르겠어요
            </button>
          )}
          <button
            type="button"
            disabled={!answered || submitting}
            onClick={
              isLast
                ? () => void finish()
                : goToNextQuestion
            }
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3.5 font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isLast ? (submitting ? '저장 중...' : '완료하기') : '다음 질문'}{' '}
            <ArrowRight size={18} />
          </button>
        </div>
      </div>
    </section>
  )
}
