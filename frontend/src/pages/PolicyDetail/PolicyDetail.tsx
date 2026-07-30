import { ArrowLeft, Bot, Calculator, CheckCircle2, ClipboardCheck, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  addPolicyBookmark,
  getPolicyDetail,
  removePolicyBookmark,
  type PolicyDetail as PolicyDetailData,
} from '../../api/policies'

type PolicyTab = '지원내용' | '신청조건' | '신청방법' | '필요서류'

const policyTabs: PolicyTab[] = ['지원내용', '신청조건', '신청방법', '필요서류']

export default function PolicyDetail() {
  const navigate = useNavigate()
  const { id } = useParams()
  const [tab, setTab] = useState<PolicyTab>('지원내용')
  const [result, setResult] = useState<{
    policyId: number | null
    policy: PolicyDetailData | null
    error: string | null
  }>({ policyId: null, policy: null, error: null })
  const [isBookmarking, setIsBookmarking] = useState(false)
  const [bookmarkError, setBookmarkError] = useState('')
  const policyId = Number(id)
  const isInvalidPolicyId = !Number.isInteger(policyId) || policyId <= 0
  const isLoading = !isInvalidPolicyId && result.policyId !== policyId
  const policy = result.policyId === policyId ? result.policy : null
  const error = isInvalidPolicyId
    ? '올바르지 않은 정책 번호예요.'
    : result.policyId === policyId
      ? result.error
      : null
  const isStarred = Boolean(policy?.is_bookmarked)

  useEffect(() => {
    let isCurrent = true

    if (isInvalidPolicyId) return

    getPolicyDetail(policyId)
      .then((response) => {
        if (isCurrent) setResult({ policyId, policy: response, error: null })
      })
      .catch(() => {
        if (!isCurrent) return
        setResult({
          policyId,
          policy: null,
          error: '정책 정보를 불러오지 못했어요. 잠시 후 다시 확인해 주세요.',
        })
      })

    return () => {
      isCurrent = false
    }
  }, [isInvalidPolicyId, policyId])

  async function toggleBookmark(policyData: PolicyDetailData): Promise<void> {
    if (isBookmarking) return
    setIsBookmarking(true)
    setBookmarkError('')
    try {
      if (policyData.is_bookmarked) await removePolicyBookmark(policyData.id)
      else await addPolicyBookmark(policyData.id)
      setResult((current) => ({
        ...current,
        policy: current.policy
          ? { ...current.policy, is_bookmarked: !policyData.is_bookmarked }
          : null,
      }))
    } catch {
      setBookmarkError('관심 정책을 변경하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsBookmarking(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[420px] flex-col items-center justify-center gap-4 rounded-xl bg-amber-50/60 text-center">
        <span className="h-10 w-10 animate-spin rounded-full border-4 border-amber-200 border-t-amber-500" />
        <p className="text-sm font-semibold text-amber-900">
          정책 내용을 차근차근 준비하고 있어요. 잠시만 기다려 주세요.
        </p>
      </div>
    )
  }

  if (error || !policy) {
    return (
      <section className="text-center">
        <p className="rounded-xl bg-rose-50 p-6 text-sm text-rose-700">
          {error ?? '정책 정보를 찾을 수 없어요.'}
        </p>
        <button
          type="button"
          onClick={() => navigate('/policies')}
          className="mt-4 text-sm font-bold text-blue-600"
        >
          정책 목록으로 돌아가기
        </button>
      </section>
    )
  }

  const category = policy.categories.find((item) => item.is_primary)?.name ?? '기타'
  const tabData: Record<PolicyTab, string[]> = {
    지원내용: policy.benefits.map(
      (benefit) => benefit.display_text ?? '혜택 상세 내용은 공고문을 확인해 주세요.',
    ),
    신청조건: policy.conditions.map((condition) => condition.description),
    신청방법: [policy.application_method ?? '신청 방법은 공고문을 확인해 주세요.'],
    필요서류: policy.documents.map((document) => document.document_name),
  }
  const benefitAmount =
    policy.max_benefit_amount === null
      ? '상세 확인 필요'
      : `${Number(policy.max_benefit_amount).toLocaleString('ko-KR')}원`
  const durationMonths = policy.benefits.find((benefit) => benefit.duration_months)?.duration_months
  const deadline = policy.is_ongoing
    ? '상시 신청'
    : (policy.application_end_date ?? '상세 확인 필요')

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
                  {category}
                </span>
                <span className="text-xs text-gray-400">정책 ID · {policy.id}</span>
              </div>
              <h1 className="mt-4 text-3xl font-black">{policy.title}</h1>
            </div>
            <button
              type="button"
              disabled={isBookmarking}
              onClick={() => void toggleBookmark(policy)}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg transition hover:bg-amber-50 disabled:opacity-50"
              aria-label={isStarred ? '관심 정책 해제' : '관심 정책 등록'}
              aria-pressed={isStarred}
            >
              <Star
                className={`h-6 w-6 ${isStarred ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'}`}
              />
            </button>
          </div>
          {bookmarkError && <p className="mt-3 text-sm text-rose-600">{bookmarkError}</p>}
          <p className="mt-3 max-w-2xl text-sm leading-7 text-gray-500">
            {policy.description ?? policy.summary ?? '정책의 자세한 내용을 확인해 주세요.'}
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            {[
              ['예상 혜택', benefitAmount],
              ['지원 기간', durationMonths ? `최대 ${durationMonths}개월` : '상세 확인 필요'],
              ['신청 마감', deadline],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="mt-2 font-bold">{value}</p>
              </div>
            ))}
          </div>
        </div>
        <aside className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <CheckCircle2 className="text-emerald-600" />
          <p className="mt-4 text-sm font-semibold text-emerald-700">조건 충족 요약</p>
          <p className="mt-2 text-xl font-black">매칭 점수 {policy.match_score ?? 0}점</p>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            {policy.card_status === 'ELIGIBLE'
              ? '현재 입력한 정보로는 신청 가능성이 높아요.'
              : policy.card_status === 'NEEDS_REVIEW'
                ? '추가로 확인할 조건이 있어요.'
                : '현재 입력한 정보로는 충족하지 못한 조건이 있어요.'}
          </p>
        </aside>
      </div>
      <div className="mt-5 rounded-xl border border-gray-200 bg-white">
        <div className="flex overflow-x-auto border-b border-gray-200">
          {policyTabs.map((name) => (
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
            {(tabData[tab].length > 0
              ? tabData[tab]
              : ['등록된 상세 내용이 없어요. 공고문을 확인해 주세요.']
            ).map((item) => (
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
          onClick={() => navigate(`/policies/${policy.id}/simulation`)}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-blue-600 bg-white px-4 py-3.5 font-bold text-blue-600"
        >
          <Calculator size={18} /> 예상 시뮬레이션 보기
        </button>
        <button
          onClick={() => navigate(`/policies/${policy.id}/prepare`)}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3.5 font-bold text-white"
        >
          <ClipboardCheck size={18} /> 가입 준비하기
        </button>
        <button
          onClick={() => navigate(`/policies/${policy.id}/ai-chat`)}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-3.5 font-bold"
        >
          <Bot size={18} /> AI에게 물어보기
        </button>
      </div>
    </section>
  )
}
