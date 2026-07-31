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
import { listCategories } from '../../api/categories'
import { extractErrorMessage } from '../../api/client'
import type { CategoryResponse } from '../../types/api'

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        setLoading(true)
        setError('')
        return listCategories()
      })
      .then((data) => {
        if (cancelled || !data) return
        setCategories(data)
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
            return (
              <button
                key={category.id}
                onClick={() =>
                  navigate(
                    category.code === 'TRANSPORT'
                      ? `/policies?category=${encodeURIComponent(category.name)}`
                      : `/categories/${category.id}/questions`,
                  )
                }
                className="rounded-xl border border-gray-200 bg-white p-6 text-left transition hover:border-blue-300 hover:bg-blue-50"
              >
                <Icon size={27} className="text-gray-500" />
                <h2 className="mt-5 font-bold">{category.name}</h2>
                <p className="mt-1 text-sm text-gray-500">{category.description}</p>
                <p className="mt-4 text-xs font-semibold text-blue-600">
                  {category.code === 'TRANSPORT' ? '맞춤 정책 보기' : '추가 질문 시작'}
                </p>
              </button>
            )
          })}
        </div>
      )}
      <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-6">
        <p className="font-bold">정확한 맞춤 추천을 받아보세요</p>
        <p className="mt-2 text-sm text-gray-600">
          몇 가지 추가 질문에 답하면 내 조건에 맞는 정책을 더 정확하게 보여드려요.
        </p>
        <button
          onClick={() => navigate('/onboarding')}
          className="mt-4 rounded-lg border border-blue-600 bg-white px-4 py-2.5 text-sm font-bold text-blue-600"
        >
          기본 정보 확인·수정하기
        </button>
      </div>
    </section>
  )
}
