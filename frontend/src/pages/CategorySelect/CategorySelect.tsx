import { BriefcaseBusiness, Calculator, CreditCard, Heart, House, TrainFront } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const categories = [
  { id: 'housing', name: '주거', detail: '월세·전세·주택구입', icon: House, count: 32 },
  { id: 'transport', name: '교통', detail: '대중교통·교통비', icon: TrainFront, count: 18 },
  { id: 'finance', name: '금융', detail: '대출·저축·자산형성', icon: CreditCard, count: 27 },
  { id: 'tax', name: '세금', detail: '세금 감면·환급', icon: Calculator, count: 12 },
  { id: 'employment', name: '고용', detail: '취업지원·일자리', icon: BriefcaseBusiness, count: 25 },
  { id: 'welfare', name: '복지', detail: '건강·돌봄·생활', icon: Heart, count: 40 },
]

export default function CategorySelect() {
  const navigate = useNavigate()
  return (
    <section>
      <p className="text-sm font-semibold text-blue-600">분야별 탐색</p>
      <h1 className="mt-2 text-3xl font-black">카테고리를 선택해주세요</h1>
      <p className="mt-2 text-sm text-gray-500">
        원하는 분야를 선택하면 관련 정책과 필요한 추가 질문을 보여드릴게요.
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map(({ id, name, detail, icon: Icon, count }) => (
          <button
            key={id}
            onClick={() => navigate(`/categories/${id}/questions`)}
            className="rounded-xl border border-gray-200 bg-white p-6 text-left transition hover:border-blue-300 hover:bg-blue-50"
          >
            <Icon size={27} className="text-gray-500" />
            <h2 className="mt-5 font-bold">{name}</h2>
            <p className="mt-1 text-sm text-gray-500">{detail}</p>
            <p className="mt-4 text-xs font-semibold text-blue-600">
              정책 {count}개 · 추가 질문 시작
            </p>
          </button>
        ))}
      </div>
      <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-6">
        <p className="font-bold">정확한 맞춤 추천을 받아보세요</p>
        <p className="mt-2 text-sm text-gray-600">
          몇 가지 추가 질문에 답하면 내 조건에 맞는 정책을 더 정확하게 보여드려요.
        </p>
        <button
          onClick={() => navigate('/onboarding')}
          className="mt-4 rounded-lg border border-blue-600 bg-white px-4 py-2.5 text-sm font-bold text-blue-600"
        >
          기본 정보 확인·수정하기
        </button>
      </div>
    </section>
  )
}
