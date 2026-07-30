import {
  BriefcaseBusiness,
  ChevronDown,
  CreditCard,
  Filter,
  Heart,
  House,
  ReceiptText,
  Star,
  TrainFront,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  addPolicyBookmark,
  getRecommendedPolicies,
  removePolicyBookmark,
  type PolicyListParams,
  type PolicySummary,
} from '../../api/policies'
import { useApp } from '../../store/useApp'
import type { EligibilityStatus } from '../../types'
import { eligibilityStatusLabels } from '../../types/policy'

type PossibilityFilter = EligibilityStatus | 'ALL'
type PolicySort = 'recommended' | 'deadline'

const possibilityFilters = [
  { value: 'ELIGIBLE', label: eligibilityStatusLabels.ELIGIBLE },
  { value: 'NEEDS_REVIEW', label: eligibilityStatusLabels.NEEDS_REVIEW },
  { value: 'INELIGIBLE', label: eligibilityStatusLabels.INELIGIBLE },
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

const categoryCodes: Record<string, string> = {
  주거: 'HOUSING',
  교통: 'TRANSPORT',
  금융: 'FINANCE',
  세금: 'TAX',
  고용: 'EMPLOYMENT',
  복지: 'WELFARE',
}

function formatBenefit(amount: PolicySummary['max_benefit_amount']): string {
  if (amount === null) return '혜택 금액은 상세 페이지에서 확인해 주세요.'
  return `최대 ${Number(amount).toLocaleString('ko-KR')}원`
}

export default function PolicyList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filterOpen, setFilterOpen] = useState(false)
  const [result, setResult] = useState<{
    requestKey: string
    policies: PolicySummary[]
    total: number
    error: string | null
  }>({ requestKey: '', policies: [], total: 0, error: null })
  const [bookmarkingIds, setBookmarkingIds] = useState<Set<number>>(new Set())
  const [bookmarkError, setBookmarkError] = useState('')
  const { userProfile } = useApp()
  const selectedCategory = searchParams.get('category')
  const activeFilter = searchParams.get('filter') || 'ELIGIBLE'
  const activeSort: PolicySort =
    searchParams.get('sort') === 'deadline' ? 'deadline' : 'recommended'
  const requestKey = `${selectedCategory ?? ''}:${activeFilter}:${activeSort}`
  const isLoading = result.requestKey !== requestKey
  const policies = isLoading ? [] : result.policies
  const total = isLoading ? 0 : result.total
  const error = isLoading ? null : result.error

  useEffect(() => {
    if (!searchParams.has('filter')) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('filter', 'ELIGIBLE')
      setSearchParams(nextParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  useEffect(() => {
    let isCurrent = true
    const params: PolicyListParams = {
      sort: activeSort === 'recommended' ? 'recommendation' : 'deadline',
      size: 100,
    }
    if (selectedCategory) params.category_code = categoryCodes[selectedCategory]
    if (activeFilter !== 'ALL') params.eligibility_status = activeFilter as EligibilityStatus

    getRecommendedPolicies(params)
      .then((response) => {
        if (!isCurrent) return
        setResult({
          requestKey,
          policies: response.items,
          total: response.total,
          error: null,
        })
      })
      .catch(() => {
        if (!isCurrent) return
        setResult({
          requestKey,
          policies: [],
          total: 0,
          error: '정책을 불러오지 못했어요. 잠시 후 다시 확인해 주세요.',
        })
      })

    return () => {
      isCurrent = false
    }
  }, [activeFilter, activeSort, requestKey, selectedCategory])

  function changePossibilityFilter(filter: PossibilityFilter) {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('filter', filter)
    setSearchParams(nextParams)
  }

  async function toggleBookmark(policy: PolicySummary): Promise<void> {
    if (bookmarkingIds.has(policy.id)) return
    setBookmarkingIds((current) => new Set(current).add(policy.id))
    setBookmarkError('')
    try {
      let isBookmarked: boolean
      if (policy.is_bookmarked) {
        await removePolicyBookmark(policy.id)
        isBookmarked = false
      } else {
        isBookmarked = (await addPolicyBookmark(policy.id)).is_bookmarked
      }
      setResult((current) => ({
        ...current,
        policies: current.policies.map((item) =>
          item.id === policy.id ? { ...item, is_bookmarked: isBookmarked } : item,
        ),
      }))
    } catch {
      setBookmarkError('관심 정책을 변경하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setBookmarkingIds((current) => {
        const next = new Set(current)
        next.delete(policy.id)
        return next
      })
    }
  }

  return (
    <section>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">
            {selectedCategory ? `${selectedCategory} 추가 답변 반영 완료` : '맞춤 정책 추천'}
          </p>
          <h1 className="mt-2 text-3xl font-black">
            {userProfile.name} 님을 위한 정책 {total}개
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {selectedCategory
              ? `${selectedCategory} 분야의 답변을 반영해 추천 정확도를 높였어요.`
              : '가능성이 높은 정책부터 간결하게 모았어요.'}
          </p>
        </div>
        <button
          onClick={() => setFilterOpen(!filterOpen)}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold"
        >
          <Filter size={17} /> 필터 <ChevronDown size={15} />
        </button>
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
      {filterOpen && (
        <div className="mt-5 grid gap-5 rounded-xl border border-gray-200 bg-white p-5 sm:grid-cols-2">
          <label className="text-sm font-semibold">
            카테고리
            <select
              value={selectedCategory || '전체'}
              onChange={(event) => {
                const nextParams = new URLSearchParams(searchParams)
                if (event.target.value === '전체') nextParams.delete('category')
                else nextParams.set('category', event.target.value)
                setSearchParams(nextParams)
              }}
              className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
            >
              <option>전체</option>
              <option>주거</option>
              <option>금융</option>
              <option>교통</option>
              <option>세금</option>
              <option>고용</option>
              <option>복지</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            정렬
            <select
              value={activeSort}
              onChange={(event) => {
                const nextParams = new URLSearchParams(searchParams)
                nextParams.set('sort', event.target.value)
                setSearchParams(nextParams)
              }}
              className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
            >
              <option value="recommended">추천순</option>
              <option value="deadline">마감순</option>
            </select>
          </label>
        </div>
      )}
      <div className="mt-6 space-y-3">
        {bookmarkError && (
          <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{bookmarkError}</p>
        )}
        {isLoading && (
          <div className="flex min-h-64 flex-col items-center justify-center gap-4 rounded-xl bg-amber-50/60 text-center">
            <span className="h-9 w-9 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
            <p className="text-sm font-semibold text-amber-900">
              꼭 맞는 정책을 정성껏 찾고 있어요. 잠시만 기다려 주세요.
            </p>
          </div>
        )}
        {!isLoading && error && (
          <p className="rounded-xl bg-rose-50 p-6 text-center text-sm text-rose-700">{error}</p>
        )}
        {!isLoading && !error && policies.length === 0 && (
          <p className="rounded-xl bg-slate-50 p-6 text-center text-sm text-gray-600">
            조건에 맞는 정책이 아직 없어요. 다른 조건으로 살펴봐 주세요.
          </p>
        )}
        {!isLoading &&
          !error &&
          policies.map((policy) => {
            const { id, title } = policy
            const category = policy.categories.find((item) => item.is_primary)?.name ?? '기타'
            const chance = policy.card_status
              ? eligibilityStatusLabels[policy.card_status]
              : '판정 준비 중'
            const deadline = policy.days_until_deadline
            const favorite = policy.is_bookmarked
            const CategoryIcon = categoryIcons[category] ?? ReceiptText
            return (
              <article
                key={id}
                className="flex min-h-[250px] flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-blue-300"
              >
                <header className="flex items-center justify-between gap-3">
                  <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                    {category}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${chance.includes('높음') ? 'bg-emerald-100 text-emerald-700' : chance.includes('추가') ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}
                    >
                      {chance}
                    </span>
                    <button
                      type="button"
                      disabled={bookmarkingIds.has(id)}
                      onClick={(event) => {
                        event.stopPropagation()
                        void toggleBookmark(policy)
                      }}
                      className="rounded-md p-1 disabled:opacity-50"
                      aria-label={`${title} ${favorite ? '관심 정책 해제' : '관심 정책 등록'}`}
                    >
                      <Star
                        className={`h-5 w-5 cursor-pointer ${favorite ? 'fill-amber-400 text-amber-400' : 'text-gray-400 hover:text-amber-400'}`}
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
                      <h2 className="text-xl font-bold text-gray-950">{title}</h2>
                      <p className="text-sm leading-7 text-gray-500">
                        {policy.summary ?? '정책 상세 내용을 확인해 주세요.'}
                      </p>
                      <p className="text-base font-bold leading-7 text-blue-700">
                        {formatBenefit(policy.max_benefit_amount)}
                      </p>
                    </div>

                    <footer className="mt-auto flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex flex-wrap items-center gap-3 text-sm">
                        <span
                          className={`font-semibold ${
                            deadline !== null && deadline < 7 ? 'text-rose-600' : 'text-gray-950'
                          }`}
                        >
                          {policy.is_ongoing
                            ? '상시 신청'
                            : deadline === null
                              ? '마감일 확인 필요'
                              : `마감 D-${deadline}`}
                        </span>
                        <span className="h-3 w-px bg-gray-200" />
                        <span className="text-gray-500">매칭 점수 {policy.match_score ?? 0}점</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigate(`/policies/${id}`)}
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
    </section>
  )
}
