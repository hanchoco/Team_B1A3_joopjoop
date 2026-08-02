import { ArrowLeft, Bot, CheckCircle2, ClipboardCheck, Calculator, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { bookmarkPolicy, getPolicy, getPolicyMatch, removeBookmark } from '../../api/policies'
import { extractErrorMessage } from '../../api/client'
import OnlineApplicationLink from '../../components/common/OnlineApplicationLink'
import PolicyContentList from '../../components/policy/PolicyContentList'
import type { PolicyDetailResponse, PolicyMatchDetailResponse } from '../../types/api'
import {
  parsePolicyContent,
  parsePolicyContentLines,
  parsePolicySummary,
} from '../../utils/policyContent'
import { getBenefitDisplay } from '../../utils/benefitDisplay'
import {
  isPolicyListNavigationState,
  resolvePolicyListReturnPath,
} from '../../utils/policyNavigation'

const TABS = ['지원내용', '신청조건', '신청방법', '필요서류'] as const
type PolicyTab = (typeof TABS)[number]

const CARD_STATUS_LABEL: Record<string, string> = {
  ELIGIBLE: '가능성 높음',
  NEEDS_REVIEW: '추가 확인 필요',
  INELIGIBLE: '불충족',
}

const CONDITION_STATUS_STYLE: Record<string, string> = {
  충족: 'text-emerald-600',
  '추가 확인 필요': 'text-amber-600',
  불충족: 'text-rose-600',
}

export default function PolicyDetail() {
  const navigate = useNavigate()
  const location = useLocation()
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const policyId = Number(id)
  const policyListPath = resolvePolicyListReturnPath(
    searchParams.get('returnTo'),
    window.location.origin,
  )
  const [tab, setTab] = useState<PolicyTab>('지원내용')
  const [policy, setPolicy] = useState<PolicyDetailResponse | null>(null)
  const [match, setMatch] = useState<PolicyMatchDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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
        return Promise.all([getPolicy(policyId), getPolicyMatch(policyId)])
      })
      .then((result) => {
        if (cancelled || !result) return
        const [policyData, matchData] = result
        setPolicy(policyData)
        setMatch(matchData)
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

  async function toggleBookmark() {
    if (!policy) return
    const nextBookmarked = !policy.is_bookmarked
    setPolicy({ ...policy, is_bookmarked: nextBookmarked })
    try {
      if (nextBookmarked) {
        await bookmarkPolicy(policy.id)
      } else {
        await removeBookmark(policy.id)
      }
    } catch (err) {
      setPolicy((current) => (current ? { ...current, is_bookmarked: !nextBookmarked } : current))
      setError(extractErrorMessage(err))
    }
  }

  function returnToPolicyList() {
    if (isPolicyListNavigationState(location.state)) {
      navigate(-1)
      return
    }
    navigate(policyListPath)
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-gray-500">불러오는 중...</p>
  }
  if (error || !policy) {
    return (
      <section>
        <button
          onClick={returnToPolicyList}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
        >
          <ArrowLeft size={16} /> 정책 목록
        </button>
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          {error || '정책을 찾을 수 없습니다.'}
        </p>
      </section>
    )
  }

  const category = policy.categories[0]?.name ?? '기타'
  const chance = policy.card_status ? CARD_STATUS_LABEL[policy.card_status] : '확인 필요'
  const deadlineText = policy.is_ongoing
    ? '상시 모집'
    : !policy.application_end_date
      ? '정보 없음'
      : policy.days_until_deadline !== null && policy.days_until_deadline < 0
        ? `마감됨 (${policy.application_end_date})`
        : policy.application_end_date
  const benefitDisplay = getBenefitDisplay(policy)
  const policySummaryItems = [
    ...(benefitDisplay.kind === 'hidden'
      ? []
      : [{ label: benefitDisplay.label, value: benefitDisplay.displayValue }]),
    { label: '가능성', value: chance },
    { label: '신청 마감', value: deadlineText },
  ]

  return (
    <section>
      <button
        onClick={returnToPolicyList}
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
              </div>
              <h1 className="mt-4 text-3xl font-black">{policy.title}</h1>
            </div>
            <button
              type="button"
              onClick={() => void toggleBookmark()}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg transition hover:bg-amber-50"
              aria-label={policy.is_bookmarked ? '관심 정책 해제' : '관심 정책 등록'}
              aria-pressed={policy.is_bookmarked}
            >
              <Star
                className={`h-6 w-6 ${policy.is_bookmarked ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'}`}
              />
            </button>
          </div>
          <PolicyContentList
            items={parsePolicySummary(policy.summary ?? policy.description)}
            className="mt-3 max-w-2xl"
          />
          {(policy.provider_name || policy.contact) && (
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
              {policy.provider_name && <span>담당기관 · {policy.provider_name}</span>}
              {policy.contact && <span>문의처 · {policy.contact}</span>}
            </div>
          )}
          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            {policySummaryItems.map((item) => (
              <div key={item.label} className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs text-gray-500">{item.label}</p>
                <p className="mt-2 font-bold">{item.value}</p>
              </div>
            ))}
          </div>
        </div>
        <aside className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <CheckCircle2 className="text-emerald-600" />
          <p className="mt-4 text-sm font-semibold text-emerald-700">조건 충족 요약</p>
          <p className="mt-2 text-xl font-black">
            {match
              ? `${match.total_condition_count}개 중 ${match.satisfied_condition_count}개 충족`
              : '-'}
          </p>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            {policy.card_status === 'ELIGIBLE'
              ? '현재 입력한 정보로는 신청 가능성이 높아요.'
              : policy.card_status === 'INELIGIBLE'
                ? '현재 조건으로는 신청이 어려울 수 있어요.'
                : '일부 조건은 추가 확인이 필요해요.'}
          </p>
        </aside>
      </div>
      <div className="mt-5 rounded-xl border border-gray-200 bg-white">
        <div className="flex overflow-x-auto border-b border-gray-200">
          {TABS.map((name) => (
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
          {tab === '신청조건' ? (
            <ul className="mt-4 space-y-3">
              {(match?.conditions ?? []).length === 0 && (
                <li className="text-sm text-gray-500">등록된 조건이 없습니다.</li>
              )}
              {(match?.conditions ?? []).map((condition) => (
                <li
                  key={condition.condition_id}
                  className="flex items-start gap-3 text-sm text-gray-600"
                >
                  <CheckCircle2
                    size={17}
                    className={`mt-0.5 shrink-0 ${CONDITION_STATUS_STYLE[condition.status] ?? 'text-gray-400'}`}
                  />
                  <span>
                    {condition.description}
                    <span
                      className={`ml-2 text-xs font-semibold ${CONDITION_STATUS_STYLE[condition.status] ?? 'text-gray-400'}`}
                    >
                      {condition.status}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : tab === '필요서류' ? (
            <PolicyContentList
              items={parsePolicyContentLines(
                policy.documents.map(
                  (document) =>
                    `${document.document_name}${document.required_reason ? ` - ${document.required_reason}` : ''}`,
                ),
                { unmarkedType: 'primary' },
              )}
              emptyMessage="등록된 서류가 없습니다."
            />
          ) : (
            <PolicyContentList
              items={parsePolicyContent(
                tab === '지원내용' ? policy.support_content_text : policy.application_method,
                { mode: tab === '지원내용' ? 'support' : 'application' },
              )}
              emptyMessage="등록된 정보가 없습니다."
            />
          )}
          {tab === '신청방법' && policy.application_url && (
            <OnlineApplicationLink url={policy.application_url} className="mt-4" />
          )}
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <button
          onClick={() => navigate(`/policies/${policy.id}/simulation`)}
          disabled={!policy.is_simulatable}
          title={
            policy.is_simulatable ? undefined : '이 정책은 아직 예상 시뮬레이션을 지원하지 않아요.'
          }
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-blue-600 bg-white px-4 py-3.5 font-bold text-blue-600 disabled:cursor-not-allowed disabled:border-gray-300 disabled:text-gray-400"
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
