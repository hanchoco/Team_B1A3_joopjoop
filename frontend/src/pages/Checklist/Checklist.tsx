import { ArrowLeft, Check, CheckCircle2, ExternalLink, FileText, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  confirmChecklistCondition,
  recordPolicyApplication,
  resetChecklistProgress,
  startPreparation,
  updateChecklistDocument,
} from '../../api/checklist'
import { extractErrorMessage } from '../../api/client'
import type {
  ChecklistDocumentItem,
  ChecklistResponse,
  ConditionResultStatus,
} from '../../types/api'

const CONDITION_LABEL: Record<ConditionResultStatus, string> = {
  SATISFIED: '충족',
  NEEDS_REVIEW: '추가 확인 필요',
  UNSATISFIED: '불충족',
}

const CONDITION_BADGE: Record<ConditionResultStatus, string> = {
  SATISFIED: 'border-green-300 bg-green-50 text-green-700',
  NEEDS_REVIEW: 'border-blue-300 bg-blue-50 text-blue-700',
  UNSATISFIED: 'border-rose-300 bg-rose-50 text-rose-700',
}

export default function Checklist() {
  const navigate = useNavigate()
  const { id } = useParams()
  const policyId = Number(id)

  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)
  const [completionAction, setCompletionAction] = useState<'reset' | 'complete' | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        if (cancelled) return undefined
        if (!Number.isFinite(policyId)) {
          throw new Error('올바르지 않은 정책입니다.')
        }
        setLoading(true)
        setError('')
        return startPreparation(policyId)
      })
      .then((data) => {
        if (cancelled || !data) return
        setChecklist(data)
        setSelectedId(data.documents[0]?.document_id ?? null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(extractErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [policyId])

  async function toggleDocument(document: ChecklistDocumentItem) {
    if (!checklist) return
    setSelectedId(document.document_id)
    const nextChecked = !document.is_checked
    setBusyId(document.document_id)
    setError('')
    try {
      const data = await updateChecklistDocument(checklist.state_id, document.document_id, {
        preparation_status: nextChecked ? 'READY' : 'NOT_STARTED',
        is_checked: nextChecked,
        note: document.note,
      })
      setChecklist(data)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  async function confirmCondition(conditionId: number) {
    if (!checklist) return
    setBusyId(conditionId)
    setError('')
    try {
      const data = await confirmChecklistCondition(checklist.state_id, conditionId, true)
      setChecklist(data)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  async function resetProgress() {
    if (!checklist) return
    setCompletionAction('reset')
    setError('')
    try {
      const data = await resetChecklistProgress(checklist)
      setChecklist(data)
      setSelectedId(data.documents[0]?.document_id ?? null)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setCompletionAction(null)
    }
  }

  async function completeApplication() {
    if (!checklist) return
    setCompletionAction('complete')
    setError('')
    try {
      const today = new Date()
      const applicationDate = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0'),
      ].join('-')
      await recordPolicyApplication(checklist.policy_id, applicationDate)
      navigate('/mypage/policies?tab=completed')
    } catch (err) {
      setError(extractErrorMessage(err))
      setCompletionAction(null)
    }
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-gray-500">불러오는 중...</p>
  }

  if (error && !checklist) {
    return (
      <section className="mx-auto max-w-3xl">
        <button
          onClick={() => navigate(`/policies/${id}`)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
        >
          <ArrowLeft size={16} /> 정책 상세로
        </button>
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      </section>
    )
  }

  if (!checklist) return null

  const documents = checklist.documents
  const selected = documents.find((item) => item.document_id === selectedId) ?? documents[0] ?? null
  const checkedCount = documents.filter((item) => item.is_checked).length

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
        <p className="mt-2 text-sm text-gray-500">{checklist.policy_title}</p>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error}
        </p>
      )}

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-xl font-black">자격조건 확인</h2>
        <ul className="mt-4 space-y-3">
          {checklist.conditions.map((condition) => (
            <li key={condition.condition_id} className="rounded-lg border border-gray-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold">{condition.description}</p>
                  {condition.reason && (
                    <p className="mt-1 text-xs text-gray-500">{condition.reason}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-bold ${CONDITION_BADGE[condition.result_status]}`}
                  >
                    {CONDITION_LABEL[condition.result_status]}
                  </span>
                  {condition.is_user_confirmed ? (
                    <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700">
                      <CheckCircle2 size={14} /> 확인 완료
                    </span>
                  ) : (
                    <button
                      type="button"
                      disabled={busyId === condition.condition_id}
                      onClick={() => void confirmCondition(condition.condition_id)}
                      className="rounded-lg border border-blue-600 px-3 py-1.5 text-xs font-bold text-blue-600 disabled:opacity-40"
                    >
                      확인 완료
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-xl font-black">제출 서류 준비</h2>
          <p className="mt-2 text-sm text-gray-500">
            항목을 선택하면 발급 방법과 제출 형태를 함께 확인할 수 있어요.
          </p>
          <div className="mt-5 flex justify-between text-sm">
            <strong>준비 현황</strong>
            <span className="font-bold text-blue-600">
              {checkedCount} / {documents.length} 완료 · {checklist.progress_percent}%
            </span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-600 transition-all"
              style={{ width: `${checklist.progress_percent}%` }}
            />
          </div>
          {checklist.progress_percent === 100 && (
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                disabled={completionAction !== null}
                onClick={() => void resetProgress()}
                className="flex-1 rounded-lg border border-blue-600 px-4 py-3 text-sm font-bold text-blue-600 disabled:opacity-40"
              >
                {completionAction === 'reset' ? '초기화 중...' : '진행도 초기화하기'}
              </button>
              <button
                type="button"
                disabled={completionAction !== null}
                onClick={() => void completeApplication()}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-40"
              >
                {completionAction === 'complete' ? '이동 중...' : '신청 완료 칸으로 이동하기'}
              </button>
            </div>
          )}
          <ul className="mt-5 space-y-2">
            {documents.map((document) => {
              const isSelected = selected?.document_id === document.document_id
              return (
                <li key={document.document_id}>
                  <div
                    className={`flex w-full items-center gap-3 rounded-lg border p-4 ${
                      isSelected ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-white'
                    }`}
                  >
                    <button
                      type="button"
                      disabled={busyId === document.document_id}
                      onClick={() => void toggleDocument(document)}
                      className={`grid h-6 w-6 shrink-0 place-items-center rounded-md border disabled:opacity-40 ${
                        document.is_checked
                          ? 'border-emerald-600 bg-emerald-600 text-white'
                          : 'border-gray-300 bg-white'
                      }`}
                      aria-label={`${document.document_name} ${document.is_checked ? '체크 해제' : '체크'}`}
                    >
                      {document.is_checked && <Check size={15} />}
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedId(document.document_id)}
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
              )
            })}
          </ul>
        </div>

        {selected && (
          <aside className="h-fit rounded-xl border border-blue-200 bg-blue-50 p-6">
            <FileText className="text-blue-600" />
            <h2 className="mt-4 text-xl font-black">{selected.document_name}</h2>
            {selected.required_reason && (
              <p className="mt-3 text-sm leading-7 text-gray-600">{selected.required_reason}</p>
            )}

            {!selected.is_required && (
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-white p-4 text-sm text-amber-800">
                <TriangleAlert size={16} /> 선택 서류입니다.
              </div>
            )}

            {(selected.issuing_organization ||
              selected.issuing_method ||
              selected.submission_format) && (
              <dl className="mt-4 divide-y divide-gray-100 border-y border-gray-200 bg-white px-4">
                {selected.issuing_organization && (
                  <div className="grid gap-1 py-3 sm:grid-cols-[88px_1fr]">
                    <dt className="text-xs font-bold text-gray-500">발급 기관</dt>
                    <dd className="text-sm font-semibold text-gray-900">
                      {selected.issuing_organization}
                    </dd>
                  </div>
                )}
                {selected.issuing_method && (
                  <div className="grid gap-1 py-3 sm:grid-cols-[88px_1fr]">
                    <dt className="text-xs font-bold text-gray-500">발급 방법</dt>
                    <dd className="text-sm leading-6 text-gray-700">{selected.issuing_method}</dd>
                  </div>
                )}
                {selected.submission_format && (
                  <div className="grid gap-1 py-3 sm:grid-cols-[88px_1fr]">
                    <dt className="text-xs font-bold text-gray-500">제출 형태</dt>
                    <dd className="text-sm leading-6 text-gray-700">
                      {selected.submission_format}
                    </dd>
                  </div>
                )}
              </dl>
            )}

            {selected.issuing_url && (
              <a
                href={selected.issuing_url}
                target="_blank"
                rel="noreferrer"
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-bold text-white"
              >
                발급 사이트 바로가기 <ExternalLink size={16} />
              </a>
            )}
          </aside>
        )}
      </div>
    </section>
  )
}
