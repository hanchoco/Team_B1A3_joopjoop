import { ArrowRight, Bookmark, CheckCircle2, ClipboardList } from 'lucide-react'
import { useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../../store/useApp'

type PolicyTab = 'interest' | 'preparing' | 'completed'

interface DisplayPolicy {
  id: string
  title: string
  category?: string
  deadline?: number
  progress?: number
  completed?: number
  total?: number
  completedAt?: string
}

const tabs: { id: PolicyTab; label: string; icon: typeof Bookmark }[] = [
  { id: 'interest', label: '관심', icon: Bookmark },
  { id: 'preparing', label: '준비 중', icon: ClipboardList },
  { id: 'completed', label: '신청 완료', icon: CheckCircle2 },
]

const mockPolicies = {
  preparing: [
    { id: 'employment-support', title: '국민취업지원제도', progress: 40, completed: 2, total: 5 },
  ],
  completed: [{ id: 'transport', title: '서울시 청년 교통비 지원', completedAt: '2026. 07. 18.' }],
}

export default function MyPolicies() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { preparedPolicies, favoritePolicies, toggleFavorite } = useApp()
  const requestedTab = searchParams.get('tab')
  const tab: PolicyTab =
    requestedTab === 'preparing' || requestedTab === 'completed' ? requestedTab : 'interest'
  const sort = searchParams.get('sort') || 'recent'

  const policies = useMemo<DisplayPolicy[]>(() => {
    if (tab === 'preparing') {
      const merged = new Map(mockPolicies.preparing.map((policy) => [policy.id, policy]))
      Object.values(preparedPolicies).forEach((policy) => merged.set(policy.id, policy))
      return [...merged.values()]
    }
    const list: DisplayPolicy[] =
      tab === 'interest' ? Object.values(favoritePolicies) : [...mockPolicies.completed]
    if (tab === 'interest' && sort === 'deadline') {
      list.sort((a, b) => (a.deadline ?? Infinity) - (b.deadline ?? Infinity))
    }
    return list
  }, [tab, sort, preparedPolicies, favoritePolicies])

  function selectTab(nextTab: PolicyTab) {
    setSearchParams(nextTab === 'interest' ? { tab: nextTab, sort } : { tab: nextTab })
  }

  function removeFavorite(policy: DisplayPolicy) {
    if (policy.category && policy.deadline !== undefined) {
      toggleFavorite({
        id: policy.id,
        title: policy.title,
        category: policy.category,
        deadline: policy.deadline,
      })
    }
  }

  return (
    <section>
      <p className="text-sm font-semibold text-blue-600">마이페이지</p>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="mt-2 text-3xl font-black">내 정책 관리</h1>
          <p className="mt-2 text-sm text-gray-500">
            관심부터 신청 완료까지 진행 상태를 한곳에서 확인하세요.
          </p>
        </div>
        {tab === 'interest' && (
          <select
            value={sort}
            onChange={(event) => setSearchParams({ tab: 'interest', sort: event.target.value })}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold"
          >
            <option value="recent">최근 저장순</option>
            <option value="deadline">마감 임박순</option>
          </select>
        )}
      </div>
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
      <div className="mt-5 space-y-3">
        {policies.map((policy) => {
          const currentTab = tabs.find((item) => item.id === tab) || tabs[0]
          const Icon = currentTab.icon
          const progress = policy.progress ?? 0
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
              key={policy.id}
              className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-5 sm:flex-row sm:items-center"
            >
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-600">
                <Icon size={20} />
              </span>
              <div className="min-w-0 flex-1">
                <strong className="block">{policy.title}</strong>
                {tab === 'interest' && (
                  <span className="mt-1 block text-xs text-rose-600">마감 D-{policy.deadline}</span>
                )}
                {tab === 'preparing' && (
                  <>
                    <span className="mt-1 block text-xs text-gray-500">
                      준비 항목 {policy.completed || 0}/{policy.total || 5} 완료 ·{' '}
                      {policy.progress || 0}%
                    </span>
                    <div className="mt-2 h-1.5 max-w-xs rounded-full bg-slate-100">
                      <div className={`h-full rounded-full bg-blue-600 ${progressWidth}`} />
                    </div>
                  </>
                )}
                {tab === 'completed' && (
                  <span className="mt-1 block text-xs text-gray-500">
                    {policy.completedAt} 신청 완료
                  </span>
                )}
              </div>
              {tab === 'preparing' ? (
                <button
                  onClick={() => navigate(`/policies/${policy.id}/prepare`)}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white"
                >
                  이어서 준비하기 <ArrowRight size={16} />
                </button>
              ) : (
                <div className="flex items-center gap-4">
                  {tab === 'interest' && (
                    <button
                      onClick={() => removeFavorite(policy)}
                      className="text-xs font-semibold text-gray-500 hover:text-rose-600"
                    >
                      관심 해제
                    </button>
                  )}
                  <button
                    onClick={() => navigate(`/policies/${policy.id}`)}
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
