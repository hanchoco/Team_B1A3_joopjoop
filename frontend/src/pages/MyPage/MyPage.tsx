import { ArrowRight, Bookmark, CheckCircle2, ClipboardList, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

export default function MyPage() {
  const navigate = useNavigate()
  const { preparedPolicies, favoritePolicies } = useApp()
  const preparing = Object.values(preparedPolicies)
  const summaries = [
    { id: 'interest', label: '관심', count: Object.keys(favoritePolicies).length, icon: Bookmark },
    {
      id: 'preparing',
      label: '준비 중',
      count: Math.max(3, preparing.length),
      icon: ClipboardList,
    },
    { id: 'completed', label: '신청 완료', count: 2, icon: CheckCircle2 },
  ]
  const continuePolicy = preparing[0] || {
    id: 'employment-support',
    title: '국민취업지원제도',
    progress: 40,
    completed: 2,
    total: 5,
  }

  return (
    <section>
      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-xl border border-gray-200 bg-white p-6">
          <span className="grid h-16 w-16 place-items-center rounded-full bg-slate-100 text-gray-400">
            <UserRound size={32} />
          </span>
          <h1 className="mt-4 text-2xl font-black">김나라 님</h1>
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
              <div className="h-full w-4/5 rounded-full bg-blue-600" />
            </div>
            <p className="mt-2 text-xs text-gray-500">프로필 정보 80% 입력 완료</p>
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
          <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-6">
            <p className="text-sm font-semibold text-blue-700">준비 중인 정책</p>
            <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center">
              <div className="flex-1">
                <h3 className="font-bold">{continuePolicy.title}</h3>
                <p className="mt-1 text-xs text-gray-600">
                  준비 항목 {continuePolicy.completed}/{continuePolicy.total} 완료 ·{' '}
                  {continuePolicy.progress}%
                </p>
              </div>
              <button
                onClick={() => navigate(`/policies/${continuePolicy.id}/prepare`)}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white"
              >
                이어서 준비하기 <ArrowRight size={16} />
              </button>
            </div>
          </div>
          <div className="mt-5 rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex justify-between">
              <div>
                <h3 className="font-bold">새로운 맞춤 정책 3개</h3>
                <p className="mt-1 text-sm text-gray-500">업데이트된 조건에 맞는 정책이에요.</p>
              </div>
              <button
                onClick={() => navigate('/policies?filter=POSSIBILITY_HIGH')}
                className="text-sm font-bold text-blue-600"
              >
                더 많은 정보 보기
              </button>
            </div>
            {['청년 월세 한시 특별지원', '청년도약계좌', '청년 교통비 지원사업'].map((name) => (
              <button
                key={name}
                onClick={() => navigate('/policies/youth-rent')}
                className="mt-4 flex w-full items-center justify-between border-t border-gray-100 pt-4 text-left text-sm font-semibold"
              >
                {name}
                <ArrowRight size={16} />
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
