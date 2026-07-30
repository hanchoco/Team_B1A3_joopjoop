import { ArrowLeft, Check, CircleCheck, ExternalLink, FileText, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const documents = [
  {
    id: 1,
    name: '나이 조건 확인',
    detail: '주민등록상 생년월일로 자동 확인해요.',
    site: '정부24 바로가기',
    conditionStatus: 'fulfilled',
    conditionDetail: '저장된 출생연도 기준으로 만 19~34세 조건을 충족해요.',
  },
  {
    id: 2,
    name: '거주기간 확인',
    detail: '전입신고 기준 거주기간을 확인해 주세요.',
    site: '정부24 바로가기',
    conditionStatus: 'review',
    conditionDetail: '부모와 별도 거주하는 무주택자인지 추가 확인이 필요해요.',
  },
  {
    id: 3,
    name: '소득 증빙 준비',
    detail: '최근 소득금액증명원 또는 급여명세서가 필요해요.',
    site: '국세청 홈택스',
    issuer: '국세청 · 재직 중인 회사',
    issueMethod: '홈택스에서 소득금액증명 발급 또는 회사에 급여명세서 요청',
    submissionFormat: '전자문서(PDF) 또는 출력본',
    conditionStatus: 'exception',
    conditionDetail: '청년가구 및 원가구 소득 기준은 증빙서류 확인이 필요해요.',
    exception:
      '30세 미만 미혼 청년이라도 생계를 독립적으로 유지하는 것으로 인정되면 원가구 소득을 고려하지 않는 예외가 적용될 수 있어요. 최신 공고 기준과 필요한 소득·재산 증빙을 함께 확인해주세요.',
  },
  {
    id: 4,
    name: '임대차계약서 준비',
    detail: '확정일자가 표시된 임대차계약서 사본을 준비해 주세요.',
    site: '대법원 인터넷등기소',
    issuer: '계약 당사자 · 주민센터',
    issueMethod: '확정일자가 표시된 계약서 원본을 스캔하거나 촬영',
    submissionFormat: '계약서 사본(PDF·이미지) 또는 출력본',
    conditionStatus: 'review',
    conditionDetail: '월세 거주 및 임대차 계약 상태를 계약서로 확인해야 해요.',
  },
  {
    id: 5,
    name: '주민등록등본 준비',
    detail: '최근 1개월 이내 발급한 등본이 필요해요.',
    site: '정부24 바로가기',
    issuer: '행정안전부 · 주민센터',
    issueMethod: '정부24 온라인 발급 또는 주민센터 방문 발급',
    submissionFormat: '전자문서(PDF) 또는 종이 원본',
    conditionStatus: 'review',
    conditionDetail: '현재 거주지와 가구 구성을 주민등록등본으로 확인해야 해요.',
  },
] as const

const policyNames = {
  1: '청년 월세 한시 특별지원',
  4: '국민취업지원제도',
}

type DocumentItem = (typeof documents)[number]

export default function Checklist() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { preparedPolicies, updatePreparation, removePreparation } = useApp()
  const policyId = Number(id ?? 1)
  const saved = preparedPolicies[policyId]
  const [checkedIds, setCheckedIds] = useState<Set<number>>(
    () => new Set(saved?.completedIds ?? []),
  )
  const [selected, setSelected] = useState<DocumentItem>(documents[0])
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
        deadline: 23,
      })
    } else {
      removePreparation(policyId)
    }
  }

  const selectedHasException = selected.conditionStatus === 'exception' && 'exception' in selected

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
          <h2 className="text-xl font-black">제출 서류 준비</h2>
          <p className="mt-2 text-sm text-gray-500">
            항목을 선택하면 관련 조건과 예외, 발급 방법을 함께 확인할 수 있어요.
          </p>
          <div className="mt-5 flex justify-between text-sm">
            <strong>준비 현황</strong>
            <span className="font-bold text-blue-600">
              {checkedIds.size} / {documents.length} 완료 · {progress}%
            </span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-slate-100">
            <div className={`h-full rounded-full bg-blue-600 transition-all ${progressWidth}`} />
          </div>
          <ul className="mt-5 space-y-2">
            {documents.map((document) => {
              const checked = checkedIds.has(document.id)
              const isSelected = selected.id === document.id
              return (
                <li key={document.id}>
                  <div
                    className={`flex w-full items-center gap-3 rounded-lg border p-4 ${
                      isSelected ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => toggleDocument(document)}
                      className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border ${
                        checked
                          ? 'border-emerald-600 bg-emerald-600 text-white'
                          : 'border-gray-300 bg-white'
                      }`}
                      aria-label={`${document.name} ${checked ? '체크 해제' : '체크'}`}
                    >
                      {checked && <Check size={15} />}
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelected(document)}
                      className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
                    >
                      <span className="text-sm font-semibold">{document.name}</span>
                      <span
                        className={`shrink-0 text-xs font-bold ${
                          checked ? 'text-emerald-700' : 'text-blue-600'
                        }`}
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

        <aside
          className={`h-fit rounded-xl border p-6 ${
            selectedHasException ? 'border-amber-200 bg-amber-50' : 'border-blue-200 bg-blue-50'
          }`}
        >
          <FileText className={selectedHasException ? 'text-amber-700' : 'text-blue-600'} />
          <h2 className="mt-4 text-xl font-black">{selected.name}</h2>
          <p className="mt-3 text-sm leading-7 text-gray-600">{selected.detail}</p>

          <div
            className={`mt-5 rounded-lg border p-4 ${
              selected.conditionStatus === 'fulfilled'
                ? 'border-green-300 bg-green-50/40'
                : 'border-blue-300 bg-blue-50/40'
            }`}
          >
            <div className="flex items-center gap-2">
              {selected.conditionStatus === 'fulfilled' ? (
                <CircleCheck size={17} className="text-green-600" />
              ) : (
                <TriangleAlert size={17} className="text-blue-600" />
              )}
              <strong className="text-sm text-gray-950">관련 자격 조건</strong>
            </div>
            <p className="mt-2 text-sm leading-6 text-gray-600">{selected.conditionDetail}</p>
          </div>

          {selectedHasException && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-white p-4">
              <strong className="block text-sm text-amber-900">예외 적용 가능</strong>
              <p className="mt-2 text-sm leading-7 text-amber-800">{selected.exception}</p>
            </div>
          )}

          {'issuer' in selected && (
            <dl className="mt-4 divide-y divide-gray-100 border-y border-gray-200 bg-white px-4">
              <div className="grid gap-1 py-3 sm:grid-cols-[88px_1fr]">
                <dt className="text-xs font-bold text-gray-500">발급 기관</dt>
                <dd className="text-sm font-semibold text-gray-900">{selected.issuer}</dd>
              </div>
              <div className="grid gap-1 py-3 sm:grid-cols-[88px_1fr]">
                <dt className="text-xs font-bold text-gray-500">발급 방법</dt>
                <dd className="text-sm leading-6 text-gray-700">{selected.issueMethod}</dd>
              </div>
              <div className="grid gap-1 py-3 sm:grid-cols-[88px_1fr]">
                <dt className="text-xs font-bold text-gray-500">제출 형태</dt>
                <dd className="text-sm leading-6 text-gray-700">{selected.submissionFormat}</dd>
              </div>
            </dl>
          )}

          <div className="mt-4 rounded-lg bg-white p-4 text-sm text-gray-600">
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
