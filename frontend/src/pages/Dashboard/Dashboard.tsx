import {
  ArrowRight,
  BadgeDollarSign,
  BriefcaseBusiness,
  Calculator,
  CreditCard,
  Heart,
  House,
  Search,
  TrainFront,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import BrandLogo from '../../components/common/BrandLogo'
import BenefitCoins from '../../components/common/BenefitCoins'

const categories = [
  { id: 'housing', name: '주거', icon: House },
  { id: 'transport', name: '교통', icon: TrainFront },
  { id: 'finance', name: '금융', icon: CreditCard },
  { id: 'tax', name: '세금', icon: Calculator },
  { id: 'employment', name: '고용', icon: BriefcaseBusiness },
  { id: 'welfare', name: '복지', icon: Heart },
]

export default function Dashboard() {
  const navigate = useNavigate()
  return (
    <section className="space-y-8">
      {' '}
      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        {' '}
        <div className="rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
          {' '}
          <p className="text-sm font-semibold text-blue-600">김나라 님을 위한 정책 탐색</p>{' '}
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
          {' '}
          <div className="flex items-center justify-between">
            <h2 className="font-bold">내 정보 요약</h2>
            <button
              onClick={() => navigate('/mypage/profile')}
              className="text-xs font-semibold text-blue-600"
            >
              수정
            </button>
          </div>{' '}
          <dl className="mt-5 space-y-3 text-sm">
            {[
              ['나이', '27세'],
              ['거주지역', '서울특별시'],
              ['주거형태', '월세'],
              ['월 소득', '220만 원'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-gray-500">{k}</dt>
                <dd className="font-semibold">{v}</dd>
              </div>
            ))}
          </dl>{' '}
          <button
            onClick={() => navigate('/profile')}
            className="mt-6 w-full rounded-lg border border-blue-600 py-2.5 text-sm font-semibold text-blue-600"
          >
            정보 다시 확인하기
          </button>{' '}
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
          {categories.map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              onClick={() => navigate(`/categories/${id}/questions`)}
              className="flex h-24 flex-col items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white text-sm font-semibold transition hover:border-blue-300 hover:bg-blue-50"
            >
              <Icon size={24} className="text-gray-500" />
              {name}
            </button>
          ))}
        </div>{' '}
      </div>{' '}
      <div>
        {' '}
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-black text-gray-950">놓치기 직전 정책</h2>{' '}
          <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-500">
            D-23
          </span>{' '}
        </div>{' '}
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.65fr_1fr]">
          {' '}
          <article className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:gap-5">
            {' '}
            <span className="grid h-16 w-16 shrink-0 place-items-center rounded-xl bg-slate-50 text-gray-500">
              <BadgeDollarSign size={32} strokeWidth={1.6} />{' '}
            </span>{' '}
            <div className="mt-4 min-w-0 flex-1 sm:mt-0">
              <h3 className="text-base font-black">청년 월세 한시 특별지원</h3>{' '}
              <p className="mt-2 text-sm leading-6 text-gray-500">
                월 최대 20만 원, 최대 12개월
                <br />
                지금 신청하면 최대 2,400,000원 지원 가능
              </p>{' '}
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
              <strong className="text-xl">3개</strong>{' '}
            </div>{' '}
            <p className="mt-6 text-sm leading-7 text-gray-500">이번 달 마감되는 정책이 있어요.</p>{' '}
            <button
              onClick={() => navigate('/policies')}
              className="mt-4 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-bold transition hover:bg-slate-50"
            >
              확인하기
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
                  <strong className="font-bold text-gray-700">연간 약 2,820,000원</strong>의 혜택을
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
