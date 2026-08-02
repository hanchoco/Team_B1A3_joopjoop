import { ArrowRight, Bookmark, CheckCircle2, ClipboardList, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCategoryAnswers, listCategories, listCategoryQuestions } from '../../api/categories'
import { listMyPolicies } from '../../api/checklist'
import { getRecommendations } from '../../api/policies'
import { useApp } from '../../store/useApp'
import type { PolicySummaryResponse, UserPolicyItemResponse } from '../../types/api'
import { getBenefitDisplay } from '../../utils/benefitDisplay'
import { calculateProfileAccuracy, type CategoryAccuracyData } from '../../utils/profileAccuracy'

export default function MyPage() {
  const navigate = useNavigate()
  const { currentUser, profile, avatarUrl } = useApp()
  const [bookmarkedCount, setBookmarkedCount] = useState(0)
  const [preparingCount, setPreparingCount] = useState(0)
  const [appliedCount, setAppliedCount] = useState(0)
  const [preparing, setPreparing] = useState<UserPolicyItemResponse[]>([])
  const [recommendations, setRecommendations] = useState<PolicySummaryResponse[]>([])
  const [recommendationsLoading, setRecommendationsLoading] = useState(true)
  const [categoryAccuracyData, setCategoryAccuracyData] = useState<CategoryAccuracyData[] | null>(
    null,
  )
  const [accuracyLoadFailed, setAccuracyLoadFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    listCategories()
      .then((categories) =>
        Promise.all(
          categories.map(async (category) => {
            const [questions, answers] = await Promise.all([
              listCategoryQuestions(category.id),
              getCategoryAnswers(category.id),
            ])
            return { categoryCode: category.code, questions, answers }
          }),
        ),
      )
      .then((data) => {
        if (!cancelled) setCategoryAccuracyData(data)
      })
      .catch(() => {
        if (!cancelled) setAccuracyLoadFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    getRecommendations(3)
      .then((items) => {
        if (!cancelled) setRecommendations(items)
      })
      .catch(() => {
        if (!cancelled) setRecommendations([])
      })
      .finally(() => {
        if (!cancelled) setRecommendationsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.all([
      listMyPolicies({ tab: 'bookmarked' }),
      listMyPolicies({ tab: 'preparing' }),
      listMyPolicies({ tab: 'applied' }),
    ])
      .then(([bookmarked, preparingList, applied]) => {
        if (cancelled) return
        setBookmarkedCount(bookmarked.length)
        setPreparingCount(preparingList.length)
        setAppliedCount(applied.length)
        setPreparing(preparingList)
      })
      .catch(() => {
        if (!cancelled) {
          setBookmarkedCount(0)
          setPreparingCount(0)
          setAppliedCount(0)
          setPreparing([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const summaries = [
    { id: 'interest', label: '관심', count: bookmarkedCount, icon: Bookmark },
    { id: 'preparing', label: '준비 중', count: preparingCount, icon: ClipboardList },
    { id: 'completed', label: '신청 완료', count: appliedCount, icon: CheckCircle2 },
  ]

  const continuePolicy = preparing[0]
  const displayName = currentUser?.nickname || currentUser?.email.split('@')[0] || '회원'
  const matchAccuracy =
    profile && categoryAccuracyData ? calculateProfileAccuracy(profile, categoryAccuracyData) : null

  return (
    <section>
      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-xl border border-gray-200 bg-white p-6">
          <span className="grid h-16 w-16 place-items-center overflow-hidden rounded-full bg-slate-100 text-gray-400">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={`${displayName} 프로필`}
                className="h-full w-full object-cover"
              />
            ) : (
              <UserRound size={32} />
            )}
          </span>
          <h1 className="mt-4 text-2xl font-black">{displayName} 님</h1>
          <p className="mt-1 text-sm text-gray-500">안녕하세요! 오늘도 놓치지 않게 도와드릴게요.</p>
          <button
            onClick={() => navigate('/mypage/profile')}
            className="mt-5 w-full rounded-lg border border-gray-300 py-2.5 text-sm font-semibold"
          >
            정보 수정
          </button>
          <div className="mt-6 border-t pt-5">
            <p className="text-sm font-bold">맞춤 정확도</p>
            <div className="mt-3 h-2 rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-blue-600"
                style={{ width: `${matchAccuracy ?? 0}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {matchAccuracy === null
                ? accuracyLoadFailed
                  ? '입력 정보를 불러오지 못했어요'
                  : '입력 정보 확인 중...'
                : `프로필·카테고리 정보 ${matchAccuracy}% 입력 완료`}
            </p>
          </div>
        </aside>
        <div>
          <p className="text-sm font-semibold text-blue-600">마이페이지</p>
          <h2 className="mt-2 text-3xl font-black">내 정책을 한눈에 관리해요</h2>
          <div className="mt-6 grid grid-cols-3 gap-3">
            {summaries.map(({ id, label, count, icon: Icon }) => (
              <button
                key={id}
                onClick={() => navigate(`/mypage/policies?tab=${id}`)}
                className="rounded-xl border border-gray-200 bg-white p-5 text-left"
              >
                <Icon size={20} className="text-blue-600" />
                <p className="mt-4 text-sm text-gray-500">{label}</p>
                <p className="mt-1 text-2xl font-black">{count}</p>
              </button>
            ))}
          </div>
          {continuePolicy && (
            <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-6">
              <p className="text-sm font-semibold text-blue-700">준비 중인 정책</p>
              <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center">
                <div className="flex-1">
                  <h3 className="font-bold">{continuePolicy.title}</h3>
                  <p className="mt-1 text-xs text-gray-600">
                    진행률 {continuePolicy.progress_percent}%
                  </p>
                </div>
                <button
                  onClick={() => navigate(`/policies/${continuePolicy.policy_id}/prepare`)}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white"
                >
                  이어서 준비하기 <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}
          <div className="mt-5 rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex justify-between">
              <div>
                <h3 className="font-bold">새로운 맞춤 정책</h3>
                <p className="mt-1 text-sm text-gray-500">업데이트된 조건에 맞는 정책이에요.</p>
              </div>
              <button
                onClick={() => navigate('/policies?filter=ELIGIBLE')}
                className="text-sm font-bold text-blue-600"
              >
                더 많은 정보 보기
              </button>
            </div>
            {recommendationsLoading ? (
              <p className="mt-5 text-sm text-gray-500">불러오는 중...</p>
            ) : recommendations.length === 0 ? (
              <p className="mt-5 text-sm text-gray-500">아직 추천할 정책이 없어요.</p>
            ) : (
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {recommendations.map((policy) => {
                  const benefitDisplay = getBenefitDisplay(policy)
                  return (
                    <button
                      key={policy.id}
                      type="button"
                      onClick={() => navigate(`/policies/${policy.id}`)}
                      className="rounded-lg border border-gray-200 p-4 text-left transition hover:border-blue-300"
                    >
                      <h4 className="text-sm font-bold">{policy.title}</h4>
                      {policy.summary && (
                        <p className="mt-1 text-xs text-gray-500">{policy.summary}</p>
                      )}
                      {benefitDisplay.kind !== 'hidden' && (
                        <p className="mt-2 text-xs font-semibold text-blue-600">
                          {benefitDisplay.label} {benefitDisplay.displayValue}
                        </p>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
