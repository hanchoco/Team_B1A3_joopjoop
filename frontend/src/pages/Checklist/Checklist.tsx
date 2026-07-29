import { ArrowLeft, Check, ExternalLink, FileText } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const documents = [
  {
    id: 1,
    name: '나이 조건 확인',
    detail: '주민등록상 생년월일로 자동 확인해요.',
    site: '정부24 바로가기',
  },
  {
    id: 2,
    name: '거주기간 확인',
    detail: '전입신고 기준 거주기간을 확인해 주세요.',
    site: '정부24 바로가기',
  },
  {
    id: 3,
    name: '소득 증빙 준비',
    detail: '최근 소득금액증명원 또는 급여명세서가 필요해요.',
    site: '국세청 홈택스',
  },
  {
    id: 4,
    name: '임대차계약서 준비',
    detail: '확정일자가 표시된 임대차계약서 사본을 준비해 주세요.',
    site: '대법원 인터넷등기소',
  },
  {
    id: 5,
    name: '주민등록등본 준비',
    detail: '최근 1개월 이내 발급한 등본이 필요해요.',
    site: '정부24 바로가기',
  },
]

const policyNames = {
  'youth-rent': '청년 월세 한시 특별지원',
  'employment-support': '국민취업지원제도',
}

type DocumentItem = (typeof documents)[number]

export default function Checklist() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { preparedPolicies, updatePreparation, removePreparation } = useApp()
  const policyId = id ?? 'youth-rent'
  const saved = preparedPolicies[policyId]
  const [checkedIds, setCheckedIds] = useState<Set<number>>(
    () => new Set(saved?.completedIds ?? []),
  )
  const [selected, setSelected] = useState(documents[0])
  const progress = Math.round((checkedIds.size / documents.length) * 100)
  const progressWidth = ['w-0', 'w-1/5', 'w-2/5', 'w-3/5', 'w-4/5', 'w-full'][checkedIds.size]

  function toggleDocument(document: DocumentItem) {
    setSelected(document)
    const next = new Set(checkedIds)
    if (next.has(document.id)) next.delete(document.id)
    else next.add(document.id)
    setCheckedIds(next)

    if (next.size > 0) {
      updatePreparation({
        id: policyId,
        title: policyNames[policyId as keyof typeof policyNames] || '청년 월세 한시 특별지원',
        progress: Math.round((next.size / documents.length) * 100),
        completed: next.size,
        total: documents.length,
        completedIds: [...next],
      })
    } else {
      removePreparation(policyId)
    }
  }

  return (
    <section>
      <button
        onClick={() => navigate(`/policies/${id}`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> 정책 상세로
      </button>
      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">신청 전 마지막 점검</p>
        <h1 className="mt-2 text-3xl font-black">가입 준비하기</h1>
        <p className="mt-2 text-sm text-gray-500">
          체크를 시작하면 내 정책의 ‘준비 중’ 목록에 자동으로 저장해드려요.
        </p>
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex justify-between text-sm">
            <strong>준비 현황</strong>
            <span className="font-bold text-blue-600">
              {checkedIds.size} / {documents.length} 완료 · {progress}%
            </span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-slate-100">
            <div className={`h-full rounded-full bg-blue-600 transition-all ${progressWidth}`} />
          </div>
          <ul className="mt-5 space-y-2">
            {documents.map((doc) => {
              const checked = checkedIds.has(doc.id)
              return (
                <li key={doc.id}>
                  <div
                    className={`flex w-full items-center gap-3 rounded-lg border p-4 ${selected.id === doc.id ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'}`}
                  >
                    <button
                      type="button"
                      onClick={() => toggleDocument(doc)}
                      className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${checked ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-gray-300 bg-white'}`}
                      aria-label={`${doc.name} ${checked ? '체크 해제' : '체크'}`}
                    >
                      {checked && <Check size={15} />}
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelected(doc)}
                      className="flex min-w-0 flex-1 items-center justify-between text-left"
                    >
                      <span className="text-sm font-semibold">{doc.name}</span>
                      <span
                        className={`text-xs font-bold ${checked ? 'text-emerald-700' : 'text-blue-600'}`}
                      >
                        {checked ? '준비 완료' : '준비하기'}
                      </span>
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
        <aside className="h-fit rounded-xl border border-blue-200 bg-blue-50 p-6">
          <FileText className="text-blue-600" />
          <p className="mt-4 text-xs font-semibold text-blue-600">선택한 항목</p>
          <h2 className="mt-1 text-xl font-black">{selected.name}</h2>
          <p className="mt-3 text-sm leading-7 text-gray-600">{selected.detail}</p>
          <div className="mt-5 rounded-lg bg-white p-4 text-sm text-gray-600">
            <strong className="block text-gray-900">발급 준비 팁</strong>
            <span className="mt-2 block">
              공동인증서 또는 간편인증을 미리 준비하면 더 빠르게 발급할 수 있어요.
            </span>
          </div>
          <button className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-bold text-white">
            {selected.site} <ExternalLink size={16} />
          </button>
        </aside>
      </div>
    </section>
  )
}
