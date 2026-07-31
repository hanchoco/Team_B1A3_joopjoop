import { ArrowLeft, ArrowRight, CheckCircle2, ChevronDown, Clock3, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { listCategories, listCategoryQuestions, saveCategoryAnswers } from '../../api/categories'
import { extractErrorMessage } from '../../api/client'
import type { CategoryAnswerUpsert, CategoryQuestionResponse } from '../../types/api'

function parseOptions(optionsJson: unknown): string[] {
  if (Array.isArray(optionsJson)) {
    return optionsJson.filter((item): item is string => typeof item === 'string')
  }
  return []
}

function policiesLinkFor(categoryName: string): string {
  const params = new URLSearchParams(categoryName ? { category: categoryName } : {})
  return `/policies?${params.toString()}`
}

interface AmountRange {
  label: string
  min: number
  max: number | null
  representativeValue: number
}

const HOUSING_AMOUNT_RANGES: Record<string, AmountRange[]> = {
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
}

const RESIDENCE_MONTH_OPTIONS = Array.from({ length: 240 }, (_, index) => index + 1)
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
  }, [categoryId])

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
      navigate(policiesLinkFor(categoryName))
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

  if (questions.length === 0) {
    return (
      <section className="mx-auto max-w-3xl">
        <button
          type="button"
          onClick={() => navigate(previousPath)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
        >
          <ArrowLeft size={16} /> {previousLabel}
        </button>
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-10 text-center">
          <p className="text-lg font-bold">
            {categoryName || '이 카테고리'}은(는) 추가로 확인할 게 없어요
          </p>
          <p className="mt-2 text-sm text-gray-500">
            기본 정보만으로 바로 맞춤 정책을 확인할 수 있어요.
          </p>
          <button
            type="button"
            onClick={() => navigate(policiesLinkFor(categoryName))}
            className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3 font-bold text-white"
          >
            맞춤 정책 보기 <ArrowRight size={18} />
          </button>
        </div>
      </section>
    )
  }

  const question = questions[step]
  const remaining = questions.length - step - 1
  const isLast = step === questions.length - 1
  const answered = question.id in answers
  const isHousing = categoryCode === 'HOUSING'
  const isHomeOwnershipQuestion = question.question_key === 'housing.home_ownership_status_code'
  const amountRanges = HOUSING_AMOUNT_RANGES[question.question_key]
  const isResidenceMonths = question.question_key === 'housing.residence_months'

  return (
    <section className="mx-auto max-w-3xl">
      <button
        type="button"
        onClick={() => {
          setMonthListOpen(false)
          if (step > 0) setStep(step - 1)
          else navigate(previousPath)
        }}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> {step > 0 ? '이전 질문' : previousLabel}
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
        {questions.map((item, index) => (
          <span
            key={item.id}
            className={`h-1.5 flex-1 rounded-full ${index <= step ? 'bg-blue-600' : 'bg-gray-200'}`}
          />
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-gray-200 bg-white p-6 sm:p-10">
        <p className="text-sm font-bold text-blue-600">
          {categoryName} 추가 질문 · {step + 1}/{questions.length}
        </p>
        <h1 className="mt-4 text-2xl font-black sm:text-3xl">{question.label}</h1>
        {question.description && (
          <p className="mt-2 text-sm text-gray-500">{question.description}</p>
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
                  min={!amountRanges && isHousing ? 0 : undefined}
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
                          : Math.max(isHousing ? 0 : -Infinity, Number(value)),
                      )
                    }
                  }}
                  placeholder={
                    amountRanges
                      ? '예: 100,000,000'
                      : isResidenceMonths
                        ? '개월 수 입력'
                        : undefined
                  }
                  className={`w-full rounded-lg border border-gray-300 px-4 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 ${
                    amountRanges
                      ? 'py-3.5 pr-12'
                      : isResidenceMonths
                        ? 'py-3.5 pr-12 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none'
                        : 'py-3.5'
                  }`}
                />
                {amountRanges && typeof answers[question.id] === 'number' && (
                  <>
                    <button
                      type="button"
                      onClick={() => setAnswerValue(question.id, undefined)}
                      className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-full text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
                      aria-label="입력한 금액 지우기"
                    >
                      <X size={16} />
                    </button>
                    <span
                      className="pointer-events-none absolute bottom-1 right-11 text-xs font-bold text-blue-600"
                      aria-live="polite"
                    >
                      {formatKoreanWon(answers[question.id])}
                    </span>
                  </>
                )}
                {isResidenceMonths && (
                  <>
                    <button
                      type="button"
                      onClick={() => setMonthListOpen((current) => !current)}
                      className="absolute right-0 top-0 grid h-full w-12 place-items-center text-gray-500"
                      aria-label="거주 개월 수 목록 열기"
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
                const selected = answers[question.id] === option
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setAnswerValue(question.id, option)}
                    className={`flex min-h-16 items-center justify-between rounded-lg border px-5 py-4 text-left text-sm font-semibold transition ${selected ? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-100' : 'border-gray-200 hover:border-blue-300'}`}
                  >
                    {option}
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

        <div className={`mt-8 grid gap-3 ${isHousing ? 'sm:grid-cols-2' : ''}`}>
          {isHousing && (
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
                : () => {
                    setMonthListOpen(false)
                    setStep((current) => current + 1)
                  }
            }
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3.5 font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isLast ? (submitting ? '저장 중...' : '답변 저장하고 맞춤 정책 보기') : '다음 질문'}{' '}
            <ArrowRight size={18} />
          </button>
        </div>
      </div>
    </section>
  )
}
