import {
  ArrowRight,
  Bookmark,
  BriefcaseBusiness,
  Calculator,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  Heart,
  House,
  MoreHorizontal,
  Star,
  TrainFront,
  Trash2,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { deletePolicyProgress, listMyPolicies } from '../../api/checklist'
import { extractErrorMessage } from '../../api/client'
import { removeBookmark } from '../../api/policies'
import ContentStatePanel from '../../components/common/ContentStatePanel'
import type { MyPoliciesTab, UserPolicyItemResponse } from '../../types/api'
import type { PolicyDetailNavigationState } from '../../utils/policyNavigation'

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

const CATEGORY_ICON_BY_CODE: Record<string, typeof House> = {
  HOUSING: House,
  TRANSPORT: TrainFront,
  FINANCE: CreditCard,
  TAX: Calculator,
  EMPLOYMENT: BriefcaseBusiness,
  WELFARE: Heart,
  PARTICIPATION: Users,
  ETC: MoreHorizontal,
}

function daysUntil(dateString: string | null): number | null {
  if (!dateString) return null
  const diffMs = new Date(dateString).getTime() - Date.now()
  return Math.ceil(diffMs / (24 * 60 * 60 * 1000))
}

export default function MyPolicies() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedTab = searchParams.get('tab')
  const tab: PolicyTab =
    requestedTab === 'preparing' || requestedTab === 'completed' ? requestedTab : 'interest'
  const sort = searchParams.get('sort') || 'recent'
  const isUrgentView = searchParams.get('view') === 'urgent'

  const [policies, setPolicies] = useState<UserPolicyItemResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [loadedRequestKey, setLoadedRequestKey] = useState<string | null>(null)
  const [error, setError] = useState('')
  const requestKey = JSON.stringify([tab, sort, isUrgentView])
  const isPoliciesLoading = loading || loadedRequestKey !== requestKey

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        setLoading(true)
        setError('')
        if (isUrgentView) {
          return listMyPolicies({ sort: 'deadline', upcoming_within_days: 30 })
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
        if (!cancelled) {
          setLoadedRequestKey(requestKey)
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [tab, sort, isUrgentView, requestKey])

  const emptyState = isUrgentView
    ? {
        title: '마감이 임박한 정책이 없어요.',
        description: '현재 30일 안에 마감되는 내 정책이 없어요.',
      }
    : tab === 'preparing'
      ? {
          title: '준비 중인 정책이 아직 없어요.',
          description: '정책 준비를 시작하면 진행 상황이 이곳에 표시돼요.',
        }
      : tab === 'completed'
        ? {
            title: '신청 완료한 정책이 아직 없어요.',
            description: '신청 완료한 정책이 생기면 이곳에 모아드려요.',
          }
        : {
            title: '관심 정책이 아직 없어요.',
            description: '관심 있는 정책을 저장하면 이곳에서 확인할 수 있어요.',
          }

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

  async function removeProgress(policy: UserPolicyItemResponse, state: PolicyTab) {
    const stateLabel =
      state === 'completed' ? '신청 완료 기록과 체크리스트' : '체크리스트 진행 상황'
    if (!window.confirm(`“${policy.title}”의 ${stateLabel}을 초기화할까요?`)) return

    try {
      await deletePolicyProgress(policy.state_id)
      setPolicies((current) => current.filter((item) => item.state_id !== policy.state_id))
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  function openPolicyDetail(policyId: number) {
    navigate(`/policies/${policyId}`, {
      state: {
        from: 'my-policies',
        myPolicyTab: tab,
        returnTo: `${location.pathname}${location.search}`,
      } satisfies PolicyDetailNavigationState,
    })
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

      {isPoliciesLoading ? (
        <ContentStatePanel
          variant="loading"
          title="정책을 불러오고 있어요."
          description="잠시만 기다려 주세요."
        />
      ) : error ? (
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      ) : policies.length === 0 ? (
        <ContentStatePanel
          variant="empty"
          title={emptyState.title}
          description={emptyState.description}
        />
      ) : (
        <div className="mt-5 space-y-3">
          {policies.map((policy) => {
            const currentState: PolicyTab = isUrgentView
              ? policy.application_status !== 'NOT_APPLIED'
                ? 'completed'
                : policy.preparation_status === 'NOT_STARTED'
                  ? 'interest'
                  : 'preparing'
              : tab
            const Icon = CATEGORY_ICON_BY_CODE[policy.category_code ?? ''] ?? Bookmark
            const remaining = daysUntil(policy.application_end_date)
            const progress = policy.progress_percent
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
                        <div
                          className="h-full rounded-full bg-blue-600 transition-all"
                          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
                        />
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
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void removeProgress(policy, currentState)}
                      className="grid h-10 w-10 place-items-center rounded-lg border border-gray-300 text-gray-500 transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600"
                      aria-label={`${policy.title} 체크리스트 진행 상황 초기화`}
                    >
                      <Trash2 size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => openPolicyDetail(policy.policy_id)}
                      className="inline-flex items-center gap-2 text-sm font-bold text-blue-600"
                    >
                      자세히 보기 <ArrowRight size={16} />
                    </button>
                    <button
                      onClick={() => navigate(`/policies/${policy.policy_id}/prepare`)}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white"
                    >
                      이어서 준비하기 <ArrowRight size={16} />
                    </button>
                  </div>
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
                    {currentState === 'completed' && (
                      <button
                        type="button"
                        onClick={() => void removeProgress(policy, currentState)}
                        className="grid h-9 w-9 place-items-center rounded-lg border border-gray-300 text-gray-500 transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600"
                        aria-label={`${policy.title} 신청 완료 기록과 체크리스트 초기화`}
                      >
                        <Trash2 size={18} />
                      </button>
                    )}
                    <button
                      onClick={() => openPolicyDetail(policy.policy_id)}
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
