import {
  BriefcaseBusiness,
  CreditCard,
  Heart,
  House,
  ReceiptText,
  Star,
  TrainFront,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { bookmarkPolicy, listPolicies, removeBookmark } from '../../api/policies'
import { extractErrorMessage } from '../../api/client'
import type { EligibilityStatus, PolicySummaryResponse } from '../../types/api'
import { useApp } from '../../store/useApp'

type PossibilityFilter = 'ELIGIBLE' | 'NEEDS_REVIEW' | 'ALL'
type PolicySort = 'recommended' | 'deadline'

const CATEGORY_CODE_BY_LABEL: Record<string, string> = {
  주거: 'HOUSING',
  교통: 'TRANSPORT',
  금융: 'FINANCE',
  세금: 'TAX',
  고용: 'EMPLOYMENT',
  복지: 'WELFARE',
}

const CARD_STATUS_LABEL: Record<EligibilityStatus, string> = {
  ELIGIBLE: '가능성 높음',
  NEEDS_REVIEW: '추가 확인 필요',
  INELIGIBLE: '불충족',
}

const possibilityFilters = [
  { value: 'ELIGIBLE', label: '가능성 높음' },
  { value: 'NEEDS_REVIEW', label: '추가 확인 필요' },
  { value: 'ALL', label: '전체' },
]

const categoryIcons: Record<string, typeof House> = {
  주거: House,
  금융: CreditCard,
  교통: TrainFront,
  고용: BriefcaseBusiness,
  복지: Heart,
  세금: ReceiptText,
}

function formatBenefit(amount: number | string | null): string | null {
  if (amount === null) return null
  const numeric = Number(amount)
  if (!Number.isFinite(numeric) || numeric <= 0) return null
  return `예상 혜택 ${numeric.toLocaleString()}원`
}

function formatDeadline(days: number | null): string {
  if (days === null) return '상시 모집'
  if (days < 0) return '마감'
  return `마감 D-${days}`
}

export default function PolicyList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { currentUser } = useApp()
  const [policies, setPolicies] = useState<PolicySummaryResponse[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const selectedCategory = searchParams.get('category')
  const activeFilter = (searchParams.get('filter') || 'ELIGIBLE') as PossibilityFilter
  const activeSort: PolicySort =
    searchParams.get('sort') === 'deadline' ? 'deadline' : 'recommended'

  useEffect(() => {
    if (!searchParams.has('filter')) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('filter', 'ELIGIBLE')
      setSearchParams(nextParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        setLoading(true)
        setError('')
        return listPolicies({
          category_code: selectedCategory ? CATEGORY_CODE_BY_LABEL[selectedCategory] : undefined,
          eligibility_status: activeFilter === 'ALL' ? undefined : activeFilter,
          sort: activeSort === 'recommended' ? 'recommendation' : 'deadline',
          size: 50,
        })
      })
      .then((data) => {
        if (cancelled || !data) return
        setPolicies(data.items)
        setTotal(data.total)
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
  }, [selectedCategory, activeFilter, activeSort])

  async function handleToggleBookmark(policy: PolicySummaryResponse) {
    const nextBookmarked = !policy.is_bookmarked
    setPolicies((current) =>
      current.map((item) =>
        item.id === policy.id ? { ...item, is_bookmarked: nextBookmarked } : item,
      ),
    )
    try {
      if (nextBookmarked) {
        await bookmarkPolicy(policy.id)
      } else {
        await removeBookmark(policy.id)
      }
    } catch (err) {
      setPolicies((current) =>
        current.map((item) =>
          item.id === policy.id ? { ...item, is_bookmarked: policy.is_bookmarked } : item,
        ),
      )
      setError(extractErrorMessage(err))
    }
  }

  function changePossibilityFilter(filter: PossibilityFilter) {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('filter', filter)
    setSearchParams(nextParams)
  }

  function toggleDeadlineSort(checked: boolean) {
    const nextParams = new URLSearchParams(searchParams)
    if (checked) {
      nextParams.set('sort', 'deadline')
    } else {
      nextParams.delete('sort')
    }
    setSearchParams(nextParams)
  }

  return (
    <section>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">
            {selectedCategory ? `${selectedCategory} 추가 답변 반영 완료` : '맞춤 정책 추천'}
          </p>
          <h1 className="mt-2 text-3xl font-black">
            {currentUser?.nickname ? `${currentUser.nickname} 님을 위한 ` : '맞춤 '}
            정책 {total}개
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {selectedCategory
              ? `${selectedCategory} 분야의 답변을 반영해 추천 정확도를 높였어요.`
              : '가능성이 높은 정책부터 간결하게 모았어요.'}
          </p>
        </div>
        <label className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold">
          <input
            type="checkbox"
            checked={activeSort === 'deadline'}
            onChange={(event) => toggleDeadlineSort(event.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          마감임박순으로 보기
        </label>
      </div>
      <div className="mt-6 flex gap-2 overflow-x-auto border-b border-gray-200">
        {possibilityFilters.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => changePossibilityFilter(value as PossibilityFilter)}
            className={`shrink-0 border-b-2 px-4 py-3 text-sm font-bold transition ${activeFilter === value ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <p className="mt-5 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      )}
      {loading ? (
        <p className="mt-8 text-center text-sm text-gray-500">불러오는 중...</p>
      ) : policies.length === 0 ? (
        <p className="mt-8 text-center text-sm text-gray-500">조건에 맞는 정책이 없어요.</p>
      ) : (
        <div className="mt-6 space-y-3">
          {policies.map((policy) => {
            const category = policy.categories[0]?.name
            const CategoryIcon = (category && categoryIcons[category]) || ReceiptText
            const chance = policy.card_status ? CARD_STATUS_LABEL[policy.card_status] : '확인 필요'
            const benefitText = formatBenefit(policy.estimated_benefit_amount)
            return (
              <article
                key={policy.id}
                className="flex min-h-[250px] flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-blue-300"
              >
                <header className="flex items-center justify-between gap-3">
                  <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                    {category ?? '기타'}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${chance.includes('높음') ? 'bg-emerald-100 text-emerald-700' : chance.includes('추가') ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}
                    >
                      {chance}
                    </span>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleToggleBookmark(policy)
                      }}
                      className="rounded-md p-1"
                      aria-label={`${policy.title} ${policy.is_bookmarked ? '관심 정책 해제' : '관심 정책 등록'}`}
                    >
                      <Star
                        className={`h-5 w-5 cursor-pointer ${policy.is_bookmarked ? 'fill-amber-400 text-amber-400' : 'text-gray-400 hover:text-amber-400'}`}
                      />
                    </button>
                  </div>
                </header>

                <div className="mt-4 grid flex-1 grid-cols-[80px_minmax(0,1fr)] gap-4 sm:grid-cols-[112px_minmax(0,1fr)] sm:gap-5">
                  <span className="grid h-full min-h-[150px] w-20 place-items-center rounded-lg bg-slate-100 text-gray-500 sm:w-28">
                    <CategoryIcon className="h-9 w-9 sm:h-12 sm:w-12" strokeWidth={1.5} />
                  </span>
                  <div className="flex min-w-0 flex-col">
                    <div className="flex flex-1 flex-col gap-3">
                      <h2 className="text-xl font-bold text-gray-950">{policy.title}</h2>
                      <p className="text-sm leading-7 text-gray-500">{policy.summary}</p>
                      {benefitText && (
                        <p className="text-base font-bold leading-7 text-blue-700">
                          {benefitText}
                        </p>
                      )}
                    </div>

                    <footer className="mt-auto flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex flex-wrap items-center gap-3 text-sm">
                        <span
                          className={`font-semibold ${
                            policy.days_until_deadline !== null && policy.days_until_deadline < 7
                              ? 'text-rose-600'
                              : 'text-gray-950'
                          }`}
                        >
                          {formatDeadline(policy.days_until_deadline)}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigate(`/policies/${policy.id}`)}
                        className="self-end rounded-lg border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 transition hover:bg-blue-50"
                      >
                        자세히 보기
                      </button>
                    </footer>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
