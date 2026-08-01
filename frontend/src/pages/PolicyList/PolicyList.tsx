import {
  BriefcaseBusiness,
  CreditCard,
  Heart,
  House,
  MoreHorizontal,
  ReceiptText,
  SlidersHorizontal,
  Star,
  TrainFront,
  Users,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { listCategories } from '../../api/categories'
import { bookmarkPolicy, listPolicies, removeBookmark } from '../../api/policies'
import { extractErrorMessage } from '../../api/client'
import type { CategoryResponse, EligibilityStatus, PolicySummaryResponse } from '../../types/api'
import { useApp } from '../../store/useApp'
import {
  buildPolicyDetailPath,
  POSSIBILITY_FILTERS,
  resolvePossibilityFilter,
  type PossibilityFilter,
} from '../../utils/policyNavigation'

type PolicySort = 'recommended' | 'deadline'

const CARD_STATUS_LABEL: Record<EligibilityStatus, string> = {
  ELIGIBLE: '가능성 높음',
  NEEDS_REVIEW: '추가 확인 필요',
  INELIGIBLE: '불충족',
}

const categoryIcons: Record<string, typeof House> = {
  주거: House,
  금융: CreditCard,
  교통: TrainFront,
  고용: BriefcaseBusiness,
  복지: Heart,
  세금: ReceiptText,
  참여: Users,
  기타: MoreHorizontal,
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
  const [categories, setCategories] = useState<CategoryResponse[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [categoriesError, setCategoriesError] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const [draftSort, setDraftSort] = useState<PolicySort>('recommended')
  const [draftCategoryCode, setDraftCategoryCode] = useState<string | null>(null)
  const filterPanelRef = useRef<HTMLDivElement>(null)
  const selectedCategoryCode = searchParams.get('category_code')
  const selectedCategoryName = selectedCategoryCode
    ? (categories.find((category) => category.code === selectedCategoryCode)?.name ?? null)
    : null
  const hasUpdatedAnswers = searchParams.get('answers') === 'updated'
  const requestedFilter = searchParams.get('filter')
  const activeFilter = resolvePossibilityFilter(requestedFilter)
  const activeSort: PolicySort =
    searchParams.get('sort') === 'deadline' ? 'deadline' : 'recommended'

  useEffect(() => {
    if (requestedFilter !== activeFilter) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('filter', activeFilter)
      setSearchParams(nextParams, { replace: true })
    }
  }, [activeFilter, requestedFilter, searchParams, setSearchParams])

  useEffect(() => {
    if (!filterOpen) return

    function closeOnOutsideClick(event: PointerEvent) {
      if (filterPanelRef.current && !filterPanelRef.current.contains(event.target as Node)) {
        setFilterOpen(false)
      }
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setFilterOpen(false)
    }

    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [filterOpen])

  useEffect(() => {
    let cancelled = false
    listCategories()
      .then((data) => {
        if (!cancelled) setCategories(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) setCategoriesError(extractErrorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        setLoading(true)
        setError('')
        return listPolicies({
          category_code: selectedCategoryCode ?? undefined,
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
  }, [selectedCategoryCode, activeFilter, activeSort])

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

  function toggleFilterPanel() {
    if (!filterOpen) {
      setDraftSort(activeSort)
      setDraftCategoryCode(selectedCategoryCode)
    }
    setFilterOpen((current) => !current)
  }

  function applyPanelFilters() {
    const nextParams = new URLSearchParams(searchParams)
    if (draftSort === 'deadline') {
      nextParams.set('sort', 'deadline')
    } else {
      nextParams.delete('sort')
    }
    if (draftCategoryCode) {
      nextParams.set('category_code', draftCategoryCode)
    } else {
      nextParams.delete('category_code')
    }
    nextParams.delete('nav')
    setSearchParams(nextParams)
    setFilterOpen(false)
  }

  function resetPanelFilters() {
    setDraftSort('recommended')
    setDraftCategoryCode(null)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('sort')
    nextParams.delete('category_code')
    nextParams.delete('nav')
    setSearchParams(nextParams)
  }

  return (
    <section>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">
            {selectedCategoryName && hasUpdatedAnswers
              ? `${selectedCategoryName} 추가 답변 반영 완료`
              : '맞춤 정책 추천'}
          </p>
          <h1 className="mt-2 text-3xl font-black">
            {currentUser?.nickname ? `${currentUser.nickname} 님을 위한 ` : '맞춤 '}
            정책 {total}개
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {selectedCategoryName && hasUpdatedAnswers
              ? `${selectedCategoryName} 분야의 답변을 반영해 추천 정확도를 높였어요.`
              : selectedCategoryName
                ? `${selectedCategoryName} 분야의 맞춤 정책을 모았어요.`
                : '가능성이 높은 정책부터 간결하게 모았어요.'}
          </p>
        </div>
        <div ref={filterPanelRef} className="relative self-start sm:self-auto">
          <button
            type="button"
            onClick={toggleFilterPanel}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-blue-300 hover:text-blue-600"
            aria-expanded={filterOpen}
            aria-controls="policy-filter-panel"
          >
            <SlidersHorizontal size={17} />
            필터
          </button>

          {filterOpen && (
            <div
              id="policy-filter-panel"
              role="dialog"
              aria-label="정책 목록 필터"
              className="absolute right-0 z-20 mt-2 w-80 max-w-[calc(100vw-2.5rem)] rounded-xl border border-gray-200 bg-white p-5 shadow-xl"
            >
              <fieldset>
                <legend className="text-sm font-bold text-gray-950">정렬 방식</legend>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {[
                    { value: 'recommended' as const, label: '추천순' },
                    { value: 'deadline' as const, label: '마감임박순' },
                  ].map((option) => (
                    <label
                      key={option.value}
                      className={`cursor-pointer rounded-lg border px-3 py-2.5 text-center text-sm font-semibold transition ${
                        draftSort === option.value
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-gray-200 text-gray-600 hover:border-blue-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="policy-sort"
                        value={option.value}
                        checked={draftSort === option.value}
                        onChange={() => setDraftSort(option.value)}
                        className="sr-only"
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="mt-5 border-t border-gray-100 pt-5">
                <legend className="text-sm font-bold text-gray-950">카테고리</legend>
                <div className="mt-3 flex flex-wrap gap-2">
                  {[{ code: null, name: '전체' }, ...categories].map((category) => {
                    const selected = draftCategoryCode === category.code
                    return (
                      <label
                        key={category.code ?? 'all'}
                        className={`cursor-pointer rounded-full border px-3 py-2 text-xs font-semibold transition ${
                          selected
                            ? 'border-blue-600 bg-blue-50 text-blue-700'
                            : 'border-gray-200 text-gray-600 hover:border-blue-300'
                        }`}
                      >
                        <input
                          type="radio"
                          name="policy-category"
                          checked={selected}
                          onChange={() => setDraftCategoryCode(category.code)}
                          className="sr-only"
                        />
                        {category.name}
                      </label>
                    )
                  })}
                </div>
              </fieldset>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={resetPanelFilters}
                  className="rounded-lg border border-gray-300 py-2.5 text-sm font-bold text-gray-600 transition hover:bg-slate-50"
                >
                  초기화
                </button>
                <button
                  type="button"
                  onClick={applyPanelFilters}
                  className="rounded-lg bg-blue-600 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700"
                >
                  적용
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="mt-6 flex gap-2 overflow-x-auto border-b border-gray-200">
        {POSSIBILITY_FILTERS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => changePossibilityFilter(value)}
            className={`shrink-0 border-b-2 px-4 py-3 text-sm font-bold transition ${activeFilter === value ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
          >
            {label}
          </button>
        ))}
      </div>
      {(error || categoriesError) && (
        <p className="mt-5 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error || categoriesError}
        </p>
      )}
      {loading ? (
        <p className="mt-8 text-center text-sm text-gray-500">불러오는 중...</p>
      ) : policies.length === 0 ? (
        <p className="mt-8 text-center text-sm text-gray-500">조건에 맞는 정책이 없어요.</p>
      ) : (
        <div className="mt-6 space-y-3">
          {policies.map((policy) => {
            const category =
              (selectedCategoryCode
                ? policy.categories.find((item) => item.code === selectedCategoryCode)
                : undefined) ?? policy.categories[0]
            const categoryName = category?.name
            const CategoryIcon = (categoryName && categoryIcons[categoryName]) || ReceiptText
            const chance = policy.card_status ? CARD_STATUS_LABEL[policy.card_status] : '확인 필요'
            const benefitText = formatBenefit(policy.estimated_benefit_amount)
            return (
              <article
                key={policy.id}
                className="flex min-h-[250px] flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-blue-300"
              >
                <header className="flex items-center justify-between gap-3">
                  <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                    {categoryName ?? '기타'}
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
                        <p className="text-base font-bold leading-7 text-blue-700">{benefitText}</p>
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
                        onClick={() => navigate(buildPolicyDetailPath(policy.id, searchParams))}
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
