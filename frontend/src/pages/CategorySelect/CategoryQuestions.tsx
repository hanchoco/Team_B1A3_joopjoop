import { ArrowLeft, ArrowRight, CheckCircle2, Clock3 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getCategories,
  getCategoryQuestions,
  saveCategoryAnswers,
  type Category,
  type CategoryCode,
  type CategoryQuestion,
} from '../../api/categories'

const slugCodes: Record<string, CategoryCode> = {
  housing: 'HOUSING',
  transport: 'TRANSPORT',
  finance: 'FINANCE',
  tax: 'TAX',
  employment: 'EMPLOYMENT',
  welfare: 'WELFARE',
}

function questionOptions(question: CategoryQuestion): string[] {
  if (Array.isArray(question.options_json)) {
    return question.options_json.filter((option): option is string => typeof option === 'string')
  }
  if (
    question.options_json &&
    typeof question.options_json === 'object' &&
    'options' in question.options_json
  ) {
    const options = (question.options_json as { options?: unknown }).options
    if (Array.isArray(options)) {
      return options.filter((option): option is string => typeof option === 'string')
    }
  }
  if (question.answer_type === 'BOOLEAN') return ['예', '아니요']
  return []
}

type AnswerValue = string | string[]

function hasAnswer(value: AnswerValue | undefined): boolean {
  return Array.isArray(value) ? value.length > 0 : Boolean(value)
}

function answerForApi(
  question: CategoryQuestion,
  value: AnswerValue,
): string | number | boolean | string[] {
  if (question.answer_type === 'NUMBER') return Number(value)
  if (question.answer_type === 'BOOLEAN') return value === '예'
  return value
}

export default function CategoryQuestions() {
  const { categoryId = 'housing' } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<{
    slug: string
    category: Category | null
    questions: CategoryQuestion[]
    error: string
  }>({ slug: '', category: null, questions: [], error: '' })
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<number, AnswerValue>>({})
  const [isSaving, setIsSaving] = useState(false)
  const isLoading = data.slug !== categoryId

  useEffect(() => {
    let isCurrent = true
    const code = slugCodes[categoryId]
    getCategories()
      .then(async (categories) => {
        const category = categories.find((item) => item.code === code)
        if (!category) throw new Error('category not found')
        const questions = await getCategoryQuestions(category.id)
        if (isCurrent) setData({ slug: categoryId, category, questions, error: '' })
      })
      .catch(() => {
        if (isCurrent) {
          setData({
            slug: categoryId,
            category: null,
            questions: [],
            error: '추가 질문을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.',
          })
        }
      })
    return () => {
      isCurrent = false
    }
  }, [categoryId])

  if (isLoading) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-3">
        <span className="h-8 w-8 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
        <p className="text-sm text-amber-900">맞춤 질문을 준비하고 있어요.</p>
      </div>
    )
  }

  if (!data.category || data.questions.length === 0) {
    return (
      <div className="rounded-xl bg-slate-50 p-8 text-center">
        <p className="text-sm text-gray-600">
          {data.error || '이 카테고리에 등록된 추가 질문이 아직 없어요.'}
        </p>
        <button
          type="button"
          onClick={() => navigate('/categories')}
          className="mt-4 text-sm font-bold text-blue-600"
        >
          카테고리로 돌아가기
        </button>
      </div>
    )
  }

  const question = data.questions[step]
  const remaining = data.questions.length - step - 1
  const isLast = step === data.questions.length - 1
  const options = questionOptions(question)

  async function finish(): Promise<void> {
    if (!data.category) return
    setIsSaving(true)
    try {
      await saveCategoryAnswers(
        data.category.id,
        data.questions.map((item) => ({
          question_id: item.id,
          answer_json: { value: answerForApi(item, answers[item.id]) },
        })),
      )
      navigate(`/policies?category=${encodeURIComponent(data.category.name)}`)
    } catch {
      setData((current) => ({
        ...current,
        error: '답변을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.',
      }))
    } finally {
      setIsSaving(false)
    }
  }

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
          <p className="text-sm font-bold text-blue-800">앞으로 {remaining}개의 질문이 남았어요.</p>
        </div>
      </div>

      <div className="mt-5 flex gap-2">
        {data.questions.map((item, index) => (
          <span
            key={item.id}
            className={`h-1.5 flex-1 rounded-full ${index <= step ? 'bg-blue-600' : 'bg-gray-200'}`}
          />
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-gray-200 bg-white p-6 sm:p-10">
        <p className="text-sm font-bold text-blue-600">
          {data.category.name} 추가 질문 · {step + 1}/{data.questions.length}
        </p>
        <h1 className="mt-4 text-2xl font-black sm:text-3xl">{question.label}</h1>
        <p className="mt-2 text-sm text-gray-500">{question.description}</p>

        {options.length > 0 ? (
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {options.map((option) => {
              const currentAnswer = answers[question.id]
              const selected = Array.isArray(currentAnswer)
                ? currentAnswer.includes(option)
                : currentAnswer === option
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() =>
                    setAnswers((current) => {
                      if (question.answer_type !== 'MULTI_SELECT') {
                        return { ...current, [question.id]: option }
                      }
                      const currentValue = current[question.id]
                      const selectedValues: string[] = Array.isArray(currentValue)
                        ? currentValue
                        : []
                      return {
                        ...current,
                        [question.id]: selectedValues.includes(option)
                          ? selectedValues.filter((item) => item !== option)
                          : [...selectedValues, option],
                      }
                    })
                  }
                  className={`flex min-h-16 items-center justify-between rounded-lg border px-5 py-4 text-left text-sm font-semibold transition ${
                    selected
                      ? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-100'
                      : 'border-gray-200 hover:border-blue-300'
                  }`}
                >
                  {option}
                  {selected && <CheckCircle2 size={18} />}
                </button>
              )
            })}
          </div>
        ) : (
          <input
            type={question.answer_type === 'NUMBER' ? 'number' : 'text'}
            value={Array.isArray(answers[question.id]) ? '' : (answers[question.id] ?? '')}
            onChange={(event) =>
              setAnswers((current) => ({ ...current, [question.id]: event.target.value }))
            }
            className="mt-8 w-full rounded-lg border border-gray-300 px-4 py-3.5"
          />
        )}

        {data.error && <p className="mt-4 text-sm font-semibold text-rose-600">{data.error}</p>}
        <button
          type="button"
          disabled={!hasAnswer(answers[question.id]) || isSaving}
          onClick={() => (isLast ? void finish() : setStep((current) => current + 1))}
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3.5 font-bold text-white disabled:opacity-40"
        >
          {isSaving
            ? '답변을 저장하고 있어요...'
            : isLast
              ? '답변 저장하고 맞춤 정책 보기'
              : '다음 질문'}{' '}
          <ArrowRight size={18} />
        </button>
      </div>
    </section>
  )
}
