import {
  ArrowRight,
  BadgeDollarSign,
  BriefcaseBusiness,
  Calculator,
  CreditCard,
  Heart,
  House,
  MoreHorizontal,
  Search,
  TrainFront,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listCategories } from '../../api/categories'
import { getDashboardSummary } from '../../api/policies'
import BrandLogo from '../../components/common/BrandLogo'
import BenefitCoins from '../../components/common/BenefitCoins'
import { employmentStatusLabel, housingTypeLabel, regionNameByCode } from '../../constants/profile'
import { useApp } from '../../store/useApp'
import type { CategoryResponse, DashboardSummaryResponse } from '../../types/api'

const ICON_BY_CODE: Record<string, typeof House> = {
  HOUSING: House,
  TRANSPORT: TrainFront,
  FINANCE: CreditCard,
  TAX: Calculator,
  EMPLOYMENT: BriefcaseBusiness,
  WELFARE: Heart,
}

function formatAmount(amount: number | string | null | undefined): string {
  const numeric = Number(amount)
  if (!Number.isFinite(numeric) || numeric <= 0) return '0원'
  return `${numeric.toLocaleString()}원`
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { isLoggedIn, currentUser, profile } = useApp()
  const [categories, setCategories] = useState<CategoryResponse[]>([])
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummaryResponse | null>(null)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const displayName = currentUser?.nickname || currentUser?.email.split('@')[0] || '회원'

  useEffect(() => {
    let cancelled = false
    listCategories()
      .then((data) => {
        if (!cancelled) setCategories(data.filter((item) => item.code in ICON_BY_CODE))
      })
      .catch(() => {
        if (!cancelled) setCategories([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!isLoggedIn) return
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        setDashboardLoading(true)
        return getDashboardSummary()
      })
      .then((data) => {
        if (cancelled || !data) return
        setDashboardSummary(data)
      })
      .catch(() => {
        if (!cancelled) setDashboardSummary(null)
      })
      .finally(() => {
        if (!cancelled) setDashboardLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isLoggedIn])

  const upcomingPolicy = isLoggedIn ? (dashboardSummary?.upcoming_deadline_policy ?? null) : null
  const upcomingCount = isLoggedIn ? (dashboardSummary?.upcoming_deadline_count ?? 0) : 0
  const dDayLabel = upcomingPolicy
    ? upcomingPolicy.days_until_deadline <= 0
      ? 'D-day'
      : `D-${upcomingPolicy.days_until_deadline}`
    : null

  return (
    <section className="space-y-8">
      {' '}
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        {' '}
        <div className="rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
          {' '}
          <p className="text-sm font-semibold text-blue-600">
            {isLoggedIn ? `${displayName} 님을 위한 정책 탐색` : '청년 정책을 한곳에서'}
          </p>{' '}
          <h1 className="mt-3 text-3xl font-black tracking-tight text-gray-950">
            지금 나에게 필요한 정책,
          </h1>{' '}
          <div className="mt-2 flex flex-wrap items-center text-3xl font-black">
            {' '}
            <span className="relative -ml-2 h-10 w-[158px] overflow-hidden">
              {' '}
              <BrandLogo className="absolute left-1/2 top-1/2 h-14 w-auto -translate-x-1/2 -translate-y-1/2" />{' '}
            </span>
            <span>이 찾아드릴게요</span>{' '}
          </div>{' '}
          <p className="mt-3 text-sm leading-7 text-gray-500">
            궁금한 정책이나 키워드를 편하게 검색해보세요.
          </p>{' '}
          <label className="mt-6 flex max-w-2xl items-center gap-3 rounded-lg border border-gray-300 bg-white px-4 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
            <Search size={19} className="text-gray-400" />{' '}
            <input
              className="h-12 min-w-0 flex-1 border-0 bg-transparent text-sm outline-none"
              placeholder="예: 청년 월세, 취업 지원금"
            />{' '}
          </label>{' '}
        </div>{' '}
        <aside className="rounded-xl border border-gray-200 bg-white p-6">
          {isLoggedIn ? (
            <>
              <h2 className="font-bold">내 정보 요약</h2>
              <dl className="mt-5 space-y-3 text-sm">
                {[
                  ['출생연도', profile?.birth_year ? `${profile.birth_year}년` : '미입력'],
                  ['거주지역', regionNameByCode(profile?.region_code)],
                  ['취업상태', employmentStatusLabel(profile?.employment_status_code)],
                  ['주거형태', housingTypeLabel(profile?.housing_type_code)],
                ].map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <dt className="text-gray-500">{key}</dt>
                    <dd className="text-right font-semibold">{value}</dd>
                  </div>
                ))}
              </dl>
              <button
                onClick={() => navigate('/mypage/profile?from=home')}
                className="mt-6 w-full rounded-lg border border-blue-600 py-2.5 text-sm font-semibold text-blue-600"
              >
                정보 다시 확인하기
              </button>
            </>
          ) : (
            <div className="flex h-full min-h-52 flex-col justify-center">
              <h2 className="font-bold">내게 맞는 정책을 찾아보세요</h2>
              <p className="mt-2 text-sm leading-6 text-gray-500">
                로그인하면 저장한 기본 정보를 바탕으로 맞춤 정책을 추천해드려요.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="mt-5 w-full rounded-lg bg-blue-600 py-2.5 text-sm font-bold text-white"
              >
                로그인
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="mt-2 w-full rounded-lg border border-blue-600 py-2.5 text-sm font-bold text-blue-600"
              >
                회원가입
              </button>
            </div>
          )}
        </aside>{' '}
      </div>{' '}
      <div>
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-lg font-bold">카테고리로 빠르게 찾아보기</h2>
            <p className="mt-1 text-sm text-gray-500">관심 분야부터 가볍게 둘러보세요.</p>
          </div>
          <button
            onClick={() => navigate('/categories')}
            className="text-sm font-semibold text-blue-600"
          >
            전체 보기
          </button>
        </div>{' '}
        <div className="mt-4 grid grid-cols-3 gap-3 md:grid-cols-6">
          {categories.map(({ id, code, name }) => {
            const Icon = ICON_BY_CODE[code] ?? MoreHorizontal
            return (
              <button
                key={id}
                onClick={() => navigate(`/categories/${id}/questions?from=home`)}
                className="flex h-24 flex-col items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white text-sm font-semibold transition hover:border-blue-300 hover:bg-blue-50"
              >
                <Icon size={24} className="text-gray-500" />
                {name}
              </button>
            )
          })}
        </div>{' '}
      </div>{' '}
      <div>
        {' '}
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-black text-gray-950">놓치기 직전 정책</h2>{' '}
          {dDayLabel && (
            <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-500">
              {dDayLabel}
            </span>
          )}{' '}
        </div>{' '}
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.65fr_1fr]">
          {' '}
          <article className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:gap-5">
            {' '}
            <span className="grid h-16 w-16 shrink-0 place-items-center rounded-xl bg-slate-50 text-gray-500">
              <BadgeDollarSign size={32} strokeWidth={1.6} />{' '}
            </span>{' '}
            <div className="mt-4 min-w-0 flex-1 sm:mt-0">
              {dashboardLoading ? (
                <h3 className="text-base font-black text-gray-400">불러오는 중...</h3>
              ) : upcomingPolicy ? (
                <>
                  <h3 className="text-base font-black">{upcomingPolicy.title}</h3>{' '}
                  <p className="mt-2 text-sm leading-6 text-gray-500">
                    {upcomingPolicy.summary ?? '마감이 얼마 남지 않았어요.'}
                  </p>{' '}
                </>
              ) : (
                <>
                  <h3 className="text-base font-black">놓치기 직전인 정책이 없어요</h3>{' '}
                  <p className="mt-2 text-sm leading-6 text-gray-500">
                    관심 정책으로 저장하면 마감이 가까워질 때 여기서 알려드려요.
                  </p>{' '}
                </>
              )}
              <button
                onClick={() => navigate('/mypage/policies?tab=interest&sort=deadline')}
                className="mt-4 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-bold transition hover:bg-slate-50"
              >
                자세히 보기
              </button>{' '}
            </div>{' '}
          </article>{' '}
          <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            {' '}
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-base font-black">신청 마감 임박 정책</h3>
              <strong className="text-xl">{upcomingCount}개</strong>{' '}
            </div>{' '}
            <p className="mt-6 text-sm leading-7 text-gray-500">
              {upcomingCount > 0
                ? '이번 달 마감되는 정책이 있어요.'
                : '아직 마감이 임박한 정책이 없어요.'}
            </p>{' '}
            <button
              onClick={() => navigate('/mypage/policies?view=urgent&sort=deadline')}
              className="mt-4 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-bold transition hover:bg-slate-50"
            >
              신청이 임박한 정책 확인하기
            </button>{' '}
          </article>{' '}
        </div>
        <div className="mt-10">
          <div className="grid items-start gap-4 lg:grid-cols-[390px_1fr] lg:gap-4">
            <div>
              <h2 className="text-lg font-black text-gray-950">내가 놓치고 있는 혜택</h2>
              <div className="ml-6 pt-[35px]">
                <p className="text-base leading-6 text-gray-500">
                  현재 기본 조건만으로도{' '}
                  <strong className="font-bold text-gray-700">
                    {formatAmount(
                      isLoggedIn ? dashboardSummary?.missed_benefit_total_amount : null,
                    )}
                  </strong>
                  의 혜택을
                  <br />
                  확인하지 않아 놓치고 있을 수 있어요.
                </p>
              </div>
            </div>
            <div className="w-full max-w-[460px] justify-self-center pt-[35px] -ml-20">
              <div className="flex items-center justify-center gap-4">
                <div className="h-2.5 w-full max-w-[320px] overflow-hidden rounded-full bg-slate-300">
                  <div className="h-full w-[58%] rounded-full bg-blue-600" />
                </div>
                <BenefitCoins className="h-[86px] w-[104px] shrink-0 object-contain" />
              </div>
              <div className="mt-1 flex justify-end">
                {' '}
                <button
                  onClick={() => navigate('/policies')}
                  className="inline-flex items-center justify-center gap-3 whitespace-nowrap text-sm font-bold text-blue-600"
                >
                  전체 맞춤 정책 확인하기 <ArrowRight size={18} />{' '}
                </button>{' '}
              </div>{' '}
            </div>{' '}
          </div>{' '}
        </div>{' '}
      </div>{' '}
    </section>
  )
}
