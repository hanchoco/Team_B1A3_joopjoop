import {
  BriefcaseBusiness,
  Calculator,
  CreditCard,
  Heart,
  House,
  MoreHorizontal,
  TrainFront,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCategoryAnswers, listCategories, listCategoryQuestions } from '../../api/categories'
import { extractErrorMessage } from '../../api/client'
import type { CategoryResponse } from '../../types/api'
import { filterVisibleCategoryQuestions } from '../../utils/categoryQuestions'

type CategoryQuestionStatus = 'none' | 'incomplete' | 'completed'

const ICON_BY_CODE: Record<string, typeof House> = {
  HOUSING: House,
  TRANSPORT: TrainFront,
  FINANCE: CreditCard,
  TAX: Calculator,
  EMPLOYMENT: BriefcaseBusiness,
  WELFARE: Heart,
  PARTICIPATION: Users,
  ETC: MoreHorizontal,
}

export default function CategorySelect() {
  const navigate = useNavigate()
  const [categories, setCategories] = useState<CategoryResponse[]>([])
  const [questionStatusByCategoryId, setQuestionStatusByCategoryId] = useState<
    Map<number, CategoryQuestionStatus>
  >(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        setLoading(true)
        setError('')
        return listCategories().then(async (categoryItems) => {
          const questionStatuses = await Promise.all(
            categoryItems.map(async (category) => {
              const [questions, answerRecords] = await Promise.all([
                listCategoryQuestions(category.id),
                getCategoryAnswers(category.id),
              ])
              const visibleQuestions = filterVisibleCategoryQuestions(questions, category.code)
              if (visibleQuestions.length === 0) {
                return [category.id, 'none'] as const
              }

              const answeredQuestionIds = new Set(answerRecords.map((answer) => answer.question_id))
              const isCompleted = visibleQuestions.every((question) =>
                answeredQuestionIds.has(question.id),
              )
              return [category.id, isCompleted ? 'completed' : 'incomplete'] as const
            }),
          )
          return { categoryItems, questionStatuses }
        })
      })
      .then((result) => {
        if (cancelled || !result) return
        setCategories(result.categoryItems)
        setQuestionStatusByCategoryId(new Map(result.questionStatuses))
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
  }, [])

  return (
    <section>
      <p className="text-sm font-semibold text-blue-600">분야별 탐색</p>
      <h1 className="mt-2 text-3xl font-black">카테고리를 선택해주세요</h1>
      <p className="mt-2 text-sm text-gray-500">
        원하는 분야를 선택하면 관련 정책과 필요한 추가 질문을 보여드릴게요.
      </p>
      {error && (
        <p className="mt-5 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      )}
      {loading ? (
        <p className="mt-8 text-center text-sm text-gray-500">불러오는 중...</p>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((category) => {
            const Icon = ICON_BY_CODE[category.code] ?? MoreHorizontal
            const questionStatus = questionStatusByCategoryId.get(category.id) ?? 'none'
            const hasIncompleteQuestions = questionStatus === 'incomplete'
            return (
              <button
                key={category.id}
                onClick={() =>
                  navigate(
                    hasIncompleteQuestions
                      ? `/categories/${category.id}/questions`
                      : `/policies?category_code=${category.code}&nav=category&origin=category`,
                  )
                }
                className="rounded-xl border border-gray-200 bg-white p-6 text-left transition hover:border-blue-300 hover:bg-blue-50"
              >
                <Icon size={27} className="text-gray-500" />
                <h2 className="mt-5 font-bold">{category.name}</h2>
                <p className="mt-1 text-sm text-gray-500">{category.description}</p>
                <p className="mt-4 text-xs font-semibold text-blue-600">
                  {hasIncompleteQuestions ? '추가 질문 시작' : '바로 확인하기'}
                </p>
              </button>
            )
          })}
        </div>
      )}
    </section>
  )
}
