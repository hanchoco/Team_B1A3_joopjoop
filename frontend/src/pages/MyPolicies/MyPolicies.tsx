import { ArrowRight, Bookmark, CheckCircle2, ClipboardList, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { listMyPolicies } from '../../api/checklist'
import { extractErrorMessage } from '../../api/client'
import { removeBookmark } from '../../api/policies'
import type { MyPoliciesTab, UserPolicyItemResponse } from '../../types/api'

type PolicyTab = 'interest' | 'preparing' | 'completed'

const TAB_TO_BACKEND: Record<PolicyTab, MyPoliciesTab> = {
  interest: 'bookmarked',
  preparing: 'preparing',
  completed: 'applied',
}

const tabs: { id: PolicyTab; label: string; icon: typeof Bookmark }[] = [
  { id: 'interest', label: '관심', icon: Bookmark },
  { id: 'preparing', label: '준비 중', icon: ClipboardList },
  { id: 'completed', label: '신청 완료', icon: CheckCircle2 },
]

function daysUntil(dateString: string | null): number | null {
  if (!dateString) return null
  const diffMs = new Date(dateString).getTime() - Date.now()
  return Math.ceil(diffMs / (24 * 60 * 60 * 1000))
}

export default function MyPolicies() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = searchParams.get('tab')
  const tab: PolicyTab =
    requestedTab === 'preparing' || requestedTab === 'completed' ? requestedTab : 'interest'
  const sort = searchParams.get('sort') || 'recent'
  const isUrgentView = searchParams.get('view') === 'urgent'

  const [policies, setPolicies] = useState<UserPolicyItemResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        setLoading(true)
        setError('')
        if (isUrgentView) {
          return Promise.all([
            listMyPolicies({ tab: 'bookmarked' }),
            listMyPolicies({ tab: 'preparing' }),
          ]).then(([bookmarked, preparing]) => {
            const deduped = new Map<number, UserPolicyItemResponse>()
            for (const item of [...bookmarked, ...preparing]) {
              deduped.set(item.state_id, item)
            }
            return [...deduped.values()].sort((a, b) => {
              const left = daysUntil(a.application_end_date) ?? Infinity
              const right = daysUntil(b.application_end_date) ?? Infinity
              return left - right
            })
          })
        }
        return listMyPolicies({
          tab: TAB_TO_BACKEND[tab],
          sort: tab === 'interest' && sort === 'deadline' ? 'deadline' : 'latest',
        })
      })
      .then((data) => {
        if (!cancelled) setPolicies(data)
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
  }, [tab, sort, isUrgentView])

  function selectTab(nextTab: PolicyTab) {
    setSearchParams(nextTab === 'interest' ? { tab: nextTab, sort } : { tab: nextTab })
  }

  async function removeFavorite(policyId: number) {
    try {
      await removeBookmark(policyId)
      setPolicies((current) => current.filter((item) => item.policy_id !== policyId))
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  return (
    <section>
      <p className="text-sm font-semibold text-blue-600">마이페이지</p>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="mt-2 text-3xl font-black">
            {isUrgentView ? '신청이 임박한 정책' : '내 정책 관리'}
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {isUrgentView
              ? '관심 정책과 준비 중 정책을 마감이 가까운 순서로 모았어요.'
              : '관심부터 신청 완료까지 진행 상태를 한곳에서 확인하세요.'}
          </p>
        </div>
        {isUrgentView ? (
          <button
            type="button"
            onClick={() => setSearchParams({ tab: 'interest' })}
            className="text-sm font-bold text-blue-600"
          >
            전체 내 정책 보기
          </button>
        ) : tab === 'interest' ? (
          <select
            value={sort}
            onChange={(event) => setSearchParams({ tab: 'interest', sort: event.target.value })}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold"
          >
            <option value="recent">최근 저장순</option>
            <option value="deadline">마감 임박순</option>
          </select>
        ) : null}
      </div>
      {!isUrgentView && (
        <div className="mt-6 flex border-b border-gray-200">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => selectTab(id)}
              className={`flex-1 px-5 py-4 text-sm font-bold ${tab === id ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <p className="mt-8 text-center text-sm text-gray-500">불러오는 중...</p>
      ) : error ? (
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      ) : policies.length === 0 ? (
        <p className="mt-8 text-center text-sm text-gray-500">표시할 정책이 없어요.</p>
      ) : (
        <div className="mt-5 space-y-3">
          {policies.map((policy) => {
            const currentState: PolicyTab = isUrgentView
              ? policy.preparation_status === 'NOT_STARTED'
                ? 'interest'
                : 'preparing'
              : tab
            const currentTab = tabs.find((item) => item.id === currentState) || tabs[0]
            const Icon = currentTab.icon
            const remaining = daysUntil(policy.application_end_date)
            const progress = policy.progress_percent
            const progressWidth =
              progress >= 100
                ? 'w-full'
                : progress >= 80
                  ? 'w-4/5'
                  : progress >= 60
                    ? 'w-3/5'
                    : progress >= 40
                      ? 'w-2/5'
                      : progress >= 20
                        ? 'w-1/5'
                        : 'w-0'
            return (
              <article
                key={policy.state_id}
                className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-5 sm:flex-row sm:items-center"
              >
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-600">
                  <Icon size={20} />
                </span>
                <div className="min-w-0 flex-1">
                  <strong className="block">{policy.title}</strong>
                  {currentState === 'interest' && remaining !== null && (
                    <span className="mt-1 block text-xs text-rose-600">마감 D-{remaining}</span>
                  )}
                  {currentState === 'preparing' && (
                    <>
                      {isUrgentView && remaining !== null && (
                        <span className="mt-1 block text-xs font-semibold text-rose-600">
                          마감 D-{remaining}
                        </span>
                      )}
                      <span className="mt-1 block text-xs text-gray-500">
                        진행률 {policy.progress_percent}%
                      </span>
                      <div className="mt-2 h-1.5 max-w-xs rounded-full bg-slate-100">
                        <div className={`h-full rounded-full bg-blue-600 ${progressWidth}`} />
                      </div>
                    </>
                  )}
                  {currentState === 'completed' && (
                    <span className="mt-1 block text-xs text-gray-500">
                      {policy.application_date} 신청 완료
                    </span>
                  )}
                </div>
                {currentState === 'preparing' ? (
                  <button
                    onClick={() => navigate(`/policies/${policy.policy_id}/prepare`)}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white"
                  >
                    이어서 준비하기 <ArrowRight size={16} />
                  </button>
                ) : (
                  <div className="flex items-center gap-4">
                    {currentState === 'interest' && (
                      <button
                        type="button"
                        onClick={() => void removeFavorite(policy.policy_id)}
                        className="grid h-9 w-9 place-items-center rounded-lg transition hover:bg-amber-50"
                        aria-label={`${policy.title} 관심 정책 해제`}
                        aria-pressed="true"
                      >
                        <Star size={21} className="fill-amber-400 text-amber-400" />
                      </button>
                    )}
                    <button
                      onClick={() => navigate(`/policies/${policy.policy_id}`)}
                      className="inline-flex items-center gap-2 text-sm font-bold text-blue-600"
                    >
                      자세히 보기 <ArrowRight size={16} />
                    </button>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
