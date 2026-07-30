import { ArrowRight, Bookmark, CheckCircle2, ClipboardList, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getMyPolicies,
  type MyPolicySort,
  type MyPolicyTab,
  type UserPolicyItem,
} from '../../api/checklists'
import { removePolicyBookmark } from '../../api/policies'

type PolicyTab = 'interest' | 'preparing' | 'completed'

const tabs: { id: PolicyTab; label: string; icon: typeof Bookmark }[] = [
  { id: 'interest', label: '관심', icon: Bookmark },
  { id: 'preparing', label: '준비 중', icon: ClipboardList },
  { id: 'completed', label: '신청 완료', icon: CheckCircle2 },
]

const apiTabs: Record<PolicyTab, MyPolicyTab> = {
  interest: 'bookmarked',
  preparing: 'preparing',
  completed: 'applied',
}

function daysUntil(date: string | null): number | null {
  if (!date) return null
  const end = new Date(`${date}T00:00:00`)
  return Math.ceil((end.getTime() - Date.now()) / 86_400_000)
}

export default function MyPolicies() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = searchParams.get('tab')
  const tab: PolicyTab =
    requestedTab === 'preparing' || requestedTab === 'completed' ? requestedTab : 'interest'
  const sort = searchParams.get('sort') === 'deadline' ? 'deadline' : 'recent'
  const isUrgentView = searchParams.get('view') === 'urgent'
  const requestKey = `${isUrgentView}:${tab}:${sort}`
  const [result, setResult] = useState<{
    requestKey: string
    policies: UserPolicyItem[]
    error: string
  }>({ requestKey: '', policies: [], error: '' })
  const [removingId, setRemovingId] = useState<number | null>(null)
  const isLoading = result.requestKey !== requestKey
  const policies = isLoading ? [] : result.policies

  useEffect(() => {
    let isCurrent = true
    const apiSort: MyPolicySort = sort === 'deadline' ? 'deadline' : 'latest'
    getMyPolicies(isUrgentView ? undefined : apiTabs[tab], apiSort)
      .then((items) => {
        if (!isCurrent) return
        const visibleItems = isUrgentView
          ? items.filter((item) => item.is_bookmarked || item.preparation_status === 'IN_PROGRESS')
          : items
        setResult({ requestKey, policies: visibleItems, error: '' })
      })
      .catch(() => {
        if (isCurrent) {
          setResult({
            requestKey,
            policies: [],
            error: '내 정책을 불러오지 못했어요. 잠시 후 다시 확인해 주세요.',
          })
        }
      })

    return () => {
      isCurrent = false
    }
  }, [isUrgentView, requestKey, sort, tab])

  function selectTab(nextTab: PolicyTab) {
    setSearchParams(nextTab === 'interest' ? { tab: nextTab, sort } : { tab: nextTab })
  }

  async function removeFavorite(policyId: number): Promise<void> {
    if (removingId !== null) return
    setRemovingId(policyId)
    try {
      await removePolicyBookmark(policyId)
      setResult((current) => ({
        ...current,
        policies: current.policies.filter((policy) => policy.policy_id !== policyId),
      }))
    } catch {
      setResult((current) => ({
        ...current,
        error: '관심 정책을 해제하지 못했어요. 잠시 후 다시 시도해 주세요.',
      }))
    } finally {
      setRemovingId(null)
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
              className={`flex-1 px-5 py-4 text-sm font-bold ${
                tab === id ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <div className="mt-5 space-y-3">
        {isLoading && (
          <div className="flex min-h-48 flex-col items-center justify-center gap-3">
            <span className="h-8 w-8 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
            <p className="text-sm text-amber-900">저장한 정책을 불러오고 있어요.</p>
          </div>
        )}
        {!isLoading && result.error && (
          <p className="rounded-xl bg-rose-50 p-5 text-center text-sm text-rose-700">
            {result.error}
          </p>
        )}
        {!isLoading && !result.error && policies.length === 0 && (
          <p className="rounded-xl bg-slate-50 p-8 text-center text-sm text-gray-600">
            아직 저장된 정책이 없어요.
          </p>
        )}
        {!isLoading &&
          !result.error &&
          policies.map((policy) => {
            const currentState: PolicyTab = isUrgentView
              ? policy.preparation_status === 'IN_PROGRESS'
                ? 'preparing'
                : 'interest'
              : tab
            const currentTab = tabs.find((item) => item.id === currentState) ?? tabs[0]
            const Icon = currentTab.icon
            const deadline = daysUntil(policy.application_end_date)
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
                  {currentState === 'interest' && (
                    <span className="mt-1 block text-xs text-rose-600">
                      {deadline === null ? '마감일 확인 필요' : `마감 D-${deadline}`}
                    </span>
                  )}
                  {currentState === 'preparing' && (
                    <>
                      <span className="mt-1 block text-xs text-gray-500">
                        준비 진행률 {policy.progress_percent}%
                      </span>
                      <div className="mt-2 h-1.5 max-w-xs rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-blue-600"
                          style={{ width: `${policy.progress_percent}%` }}
                        />
                      </div>
                    </>
                  )}
                  {currentState === 'completed' && (
                    <span className="mt-1 block text-xs text-gray-500">
                      {policy.application_date ?? '신청일 미입력'} 신청 완료
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
                        disabled={removingId !== null}
                        onClick={() => void removeFavorite(policy.policy_id)}
                        className="grid h-9 w-9 place-items-center rounded-lg transition hover:bg-amber-50 disabled:opacity-50"
                        aria-label={`${policy.title} 관심 정책 해제`}
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
    </section>
  )
}
