import { ArrowLeft, Check, CircleCheck, ExternalLink, FileText, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  confirmChecklistCondition,
  recordPolicyApplication,
  startPolicyPreparation,
  updateChecklistDocument,
  type ChecklistResponse,
} from '../../api/checklists'

export default function Checklist() {
  const navigate = useNavigate()
  const { id } = useParams()
  const policyId = Number(id)
  const isInvalidPolicyId = !Number.isInteger(policyId) || policyId <= 0
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [isApplying, setIsApplying] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true
    if (isInvalidPolicyId) return

    startPolicyPreparation(policyId)
      .then((response) => {
        if (!isCurrent) return
        setChecklist(response)
        setSelectedDocumentId(response.documents[0]?.document_id ?? null)
      })
      .catch(() => {
        if (isCurrent) setError('체크리스트를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false)
      })

    return () => {
      isCurrent = false
    }
  }, [isInvalidPolicyId, policyId])

  const selected =
    checklist?.documents.find((document) => document.document_id === selectedDocumentId) ?? null

  async function toggleDocument(documentId: number, checked: boolean): Promise<void> {
    if (!checklist || updatingId !== null) return
    setUpdatingId(documentId)
    setError('')
    try {
      const response = await updateChecklistDocument(checklist.state_id, documentId, {
        preparation_status: checked ? 'NOT_STARTED' : 'READY',
        is_checked: !checked,
      })
      setChecklist(response)
    } catch {
      setError('서류 준비 상태를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setUpdatingId(null)
    }
  }

  async function toggleCondition(conditionId: number, confirmed: boolean): Promise<void> {
    if (!checklist || updatingId !== null) return
    setUpdatingId(conditionId)
    setError('')
    try {
      setChecklist(await confirmChecklistCondition(checklist.state_id, conditionId, !confirmed))
    } catch {
      setError('조건 확인 상태를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setUpdatingId(null)
    }
  }

  async function completeApplication(): Promise<void> {
    if (!checklist || isApplying) return
    setIsApplying(true)
    setError('')
    try {
      await recordPolicyApplication(checklist.policy_id, new Date().toISOString().slice(0, 10))
      navigate('/mypage/policies?tab=completed')
    } catch {
      setError('신청 완료 상태를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsApplying(false)
    }
  }

  if (!isInvalidPolicyId && isLoading) {
    return (
      <div className="flex min-h-80 flex-col items-center justify-center gap-4">
        <span className="h-9 w-9 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
        <p className="text-sm font-semibold text-amber-900">
          준비 목록을 차근차근 불러오고 있어요.
        </p>
      </div>
    )
  }

  if (!checklist) {
    return (
      <p className="rounded-xl bg-rose-50 p-6 text-center text-sm text-rose-700">
        {isInvalidPolicyId ? '올바르지 않은 정책 번호예요.' : error}
      </p>
    )
  }

  return (
    <section>
      <button
        onClick={() => navigate(`/policies/${policyId}`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> 정책 상세로
      </button>
      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">신청 전 마지막 점검</p>
        <h1 className="mt-2 text-3xl font-black">{checklist.policy_title}</h1>
        <p className="mt-2 text-sm text-gray-500">
          변경한 준비 상태는 계정에 자동으로 안전하게 저장돼요.
        </p>
      </div>

      {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-black">준비 진행률</h2>
          <strong className="text-blue-700">{checklist.progress_percent}%</strong>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-blue-600 transition-all"
            style={{ width: `${checklist.progress_percent}%` }}
          />
        </div>
      </div>

      {checklist.conditions.length > 0 && (
        <div className="mt-5 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-xl font-black">자격 조건 확인</h2>
          <ul className="mt-4 space-y-3">
            {checklist.conditions.map((condition) => (
              <li
                key={condition.condition_id}
                className="flex items-center gap-3 rounded-lg bg-slate-50 p-4"
              >
                <button
                  type="button"
                  disabled={updatingId !== null}
                  onClick={() =>
                    void toggleCondition(condition.condition_id, condition.is_user_confirmed)
                  }
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded border ${
                    condition.is_user_confirmed
                      ? 'border-emerald-600 bg-emerald-600 text-white'
                      : 'border-gray-300 bg-white'
                  }`}
                >
                  {condition.is_user_confirmed && <Check size={15} />}
                </button>
                <div>
                  <p className="text-sm font-semibold">{condition.description}</p>
                  <p className="mt-1 text-xs text-gray-500">{condition.reason}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-xl font-black">제출 서류 준비</h2>
          <ul className="mt-5 space-y-3">
            {checklist.documents.map((document) => (
              <li key={document.document_id} className="rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    disabled={updatingId !== null}
                    onClick={() => void toggleDocument(document.document_id, document.is_checked)}
                    className={`grid h-6 w-6 shrink-0 place-items-center rounded border ${
                      document.is_checked
                        ? 'border-emerald-600 bg-emerald-600 text-white'
                        : 'border-gray-300 bg-white'
                    }`}
                    aria-label={`${document.document_name} ${
                      document.is_checked ? '체크 해제' : '체크'
                    }`}
                  >
                    {document.is_checked && <Check size={15} />}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedDocumentId(document.document_id)}
                    className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
                  >
                    <span className="text-sm font-semibold">{document.document_name}</span>
                    <span
                      className={`shrink-0 text-xs font-bold ${
                        document.is_checked ? 'text-emerald-700' : 'text-blue-600'
                      }`}
                    >
                      {document.is_checked ? '준비 완료' : '준비하기'}
                    </span>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <aside className="h-fit rounded-xl border border-blue-200 bg-blue-50 p-6">
          {selected ? (
            <>
              <FileText className="text-blue-600" />
              <h2 className="mt-4 text-xl font-black">{selected.document_name}</h2>
              <p className="mt-3 text-sm leading-7 text-gray-600">
                {selected.required_reason ?? '정책 신청에 필요한 서류예요.'}
              </p>
              <dl className="mt-4 divide-y divide-gray-100 border-y border-gray-200 bg-white px-4">
                <div className="grid gap-1 py-3">
                  <dt className="text-xs font-bold text-gray-500">발급 기관</dt>
                  <dd className="text-sm">{selected.issuing_organization ?? '공고문 확인'}</dd>
                </div>
                <div className="grid gap-1 py-3">
                  <dt className="text-xs font-bold text-gray-500">발급 방법</dt>
                  <dd className="text-sm">{selected.issuing_method ?? '공고문 확인'}</dd>
                </div>
                <div className="grid gap-1 py-3">
                  <dt className="text-xs font-bold text-gray-500">제출 형태</dt>
                  <dd className="text-sm">{selected.submission_format ?? '공고문 확인'}</dd>
                </div>
              </dl>
              {selected.issuing_url && (
                <a
                  href={selected.issuing_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-bold text-white"
                >
                  발급 사이트 열기 <ExternalLink size={16} />
                </a>
              )}
            </>
          ) : (
            <div className="text-center text-sm text-gray-600">
              <TriangleAlert className="mx-auto text-blue-600" />
              <p className="mt-3">등록된 필요 서류가 없어요.</p>
            </div>
          )}
        </aside>
      </div>

      <div className="mt-6 flex flex-col items-center rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
        <CircleCheck className="text-emerald-600" />
        <h2 className="mt-3 font-black">정책 신청을 마쳤나요?</h2>
        <p className="mt-2 text-sm text-gray-600">
          신청 완료로 표시하면 내 정책에서 확인할 수 있어요.
        </p>
        <button
          type="button"
          disabled={isApplying}
          onClick={() => void completeApplication()}
          className="mt-4 rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-50"
        >
          {isApplying ? '저장하고 있어요...' : '신청 완료로 표시'}
        </button>
      </div>
    </section>
  )
}
