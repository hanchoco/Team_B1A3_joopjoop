import { ArrowLeft, ArrowRight, CheckCircle2, Clock3 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
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

export default function CategoryQuestions() {
  const { categoryId: categoryIdParam } = useParams()
  const navigate = useNavigate()
  const categoryId = Number(categoryIdParam)

  const [categoryName, setCategoryName] = useState('')
  const [categoryCode, setCategoryCode] = useState('')
  const [questions, setQuestions] = useState<CategoryQuestionResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<number, unknown>>({})

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
    setAnswers((current) => ({ ...current, [questionId]: value }))
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
          onClick={() => navigate('/categories')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
        >
          <ArrowLeft size={16} /> 카테고리 선택
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
          onClick={() => navigate('/categories')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
        >
          <ArrowLeft size={16} /> 카테고리 선택
        </button>
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-10 text-center">
          <p className="text-lg font-bold">
            {categoryName || '이 카테고리'}는 추가로 확인할 게 없어요
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

  return (
    <section className="mx-auto max-w-3xl">
      <button
        type="button"
        onClick={() => (step > 0 ? setStep(step - 1) : navigate('/categories'))}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> {step > 0 ? '이전 질문' : '카테고리 선택'}
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
            <label className="block text-sm font-semibold">
              숫자로 입력해주세요{question.unit ? ` (${question.unit})` : ''}
              <input
                type="number"
                min={isHousing ? 0 : undefined}
                value={
                  typeof answers[question.id] === 'number' ? (answers[question.id] as number) : ''
                }
                onChange={(event) => {
                  const value = event.target.value
                  setAnswerValue(
                    question.id,
                    value === '' ? undefined : Math.max(isHousing ? 0 : -Infinity, Number(value)),
                  )
                }}
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </label>
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
            onClick={isLast ? () => void finish() : () => setStep((current) => current + 1)}
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
