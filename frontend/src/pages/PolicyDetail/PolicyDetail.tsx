import { ArrowLeft, Bot, CheckCircle2, ClipboardCheck, Calculator, Star } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const tabData = {
  지원내용: ['월 최대 20만 원 지원', '최대 12개월, 총 240만 원', '본인 계좌로 매월 지급'],
  신청조건: ['만 19~34세 청년', '부모와 별도 거주하는 무주택자', '청년가구 중위소득 60% 이하'],
  신청방법: ['복지로 온라인 신청', '주소지 관할 주민센터 방문', '접수 후 소득·재산 조사'],
  필요서류: ['임대차계약서 사본', '최근 3개월 월세 이체 내역', '가족관계증명서'],
}

type PolicyTab = keyof typeof tabData

export default function PolicyDetail() {
  const navigate = useNavigate()
  const { id } = useParams()
  const [tab, setTab] = useState<PolicyTab>('지원내용')
  const { favoritePolicies, toggleFavorite } = useApp()
  const policyId = id ?? 'youth-rent'
  const policy = {
    id: policyId,
    title: '청년 월세 한시 특별지원',
    category: '주거',
    deadline: 23,
  }
  const isStarred = Boolean(favoritePolicies[policyId])
  return (
    <section>
      <button
        onClick={() => navigate('/policies')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> 정책 목록
      </button>
      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_300px]">
        <div className="rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600">
                  주거
                </span>
                <span className="text-xs text-gray-400">정책 ID · {id}</span>
              </div>
              <h1 className="mt-4 text-3xl font-black">청년 월세 한시 특별지원</h1>
            </div>
            <button
              type="button"
              onClick={() => toggleFavorite(policy)}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg transition hover:bg-amber-50"
              aria-label={isStarred ? '관심 정책 해제' : '관심 정책 등록'}
              aria-pressed={isStarred}
            >
              <Star
                className={`h-6 w-6 ${isStarred ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'}`}
              />
            </button>
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-gray-500">
            월세 부담이 큰 청년이 조금 더 안정적으로 생활할 수 있도록 주거비를 지원해요.
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            {[
              ['예상 혜택', '월 최대 20만 원'],
              ['지원 기간', '최대 12개월'],
              ['신청 마감', '2026. 08. 20.'],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs text-gray-500">{k}</p>
                <p className="mt-2 font-bold">{v}</p>
              </div>
            ))}
          </div>
        </div>
        <aside className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <CheckCircle2 className="text-emerald-600" />
          <p className="mt-4 text-sm font-semibold text-emerald-700">조건 충족 요약</p>
          <p className="mt-2 text-xl font-black">3개 중 3개 충족</p>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            현재 입력한 정보로는 신청 가능성이 높아요.
          </p>
        </aside>
      </div>
      <div className="mt-5 rounded-xl border border-gray-200 bg-white">
        <div className="flex overflow-x-auto border-b border-gray-200">
          {(Object.keys(tabData) as PolicyTab[]).map((name) => (
            <button
              key={name}
              onClick={() => setTab(name)}
              className={`min-w-28 flex-1 px-5 py-4 text-sm font-bold ${tab === name ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
            >
              {name}
            </button>
          ))}
        </div>
        <div className="p-6">
          <h2 className="font-bold">{tab}</h2>
          <ul className="mt-4 space-y-3">
            {tabData[tab].map((item) => (
              <li key={item} className="flex items-center gap-3 text-sm text-gray-600">
                <CheckCircle2 size={17} className="text-blue-600" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <button
          onClick={() => navigate(`/policies/${id}/simulation`)}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-blue-600 bg-white px-4 py-3.5 font-bold text-blue-600"
        >
          <Calculator size={18} /> 예상 시뮬레이션 보기
        </button>
        <button
          onClick={() => navigate(`/policies/${id}/prepare`)}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3.5 font-bold text-white"
        >
          <ClipboardCheck size={18} /> 가입 준비하기
        </button>
        <button
          onClick={() => navigate(`/policies/${id}/ai-chat`)}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-3.5 font-bold"
        >
          <Bot size={18} /> AI에게 물어보기
        </button>
      </div>
    </section>
  )
}
