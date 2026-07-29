import { ArrowLeft, Check, ChevronDown, Info, LockKeyhole } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const privacySections = [
  {
    id: 'collection',
    title: '개인정보 수집 항목 및 목적',
    content:
      '필수 항목은 로그인 아이디, 비밀번호, 출생연도, 거주지역입니다. 맞춤 정책 추천, 회원 식별, 계정 보호와 서비스 제공을 위해 사용합니다. 소득구간, 취업상태, 가구·주거형태는 더 정확한 정책 추천을 위해 수집합니다.',
  },
  {
    id: 'retention',
    title: '개인정보 보유 및 이용 기간',
    content:
      '회원 정보는 회원 탈퇴 시까지 보유합니다. 관계 법령에 따라 보존할 의무가 있는 기록은 해당 법정 기간 동안 분리 보관한 뒤 안전하게 파기합니다.',
  },
  {
    id: 'third-party',
    title: '개인정보 제3자 제공',
    content:
      '현재 개인정보를 제3자에게 제공하지 않습니다. 향후 제공이 필요한 경우 제공받는 자, 목적, 항목과 보유 기간을 사전에 안내하고 별도 동의를 받습니다.',
  },
  {
    id: 'outsourcing',
    title: '개인정보 처리 위탁',
    content:
      '서비스 운영에 필요한 이메일 발송과 인프라 운영 업무를 전문 업체에 위탁할 수 있습니다. 위탁 시 계약을 통해 목적 외 처리 금지와 안전성 확보 조치를 관리합니다.',
  },
  {
    id: 'rights',
    title: '이용자의 권리와 행사 방법',
    content:
      '설정에서 개인정보를 조회·수정하고 선택 동의를 철회할 수 있습니다. 개인정보 열람, 정정, 삭제 또는 처리 정지는 고객지원 채널을 통해 요청할 수 있으며 본인 확인 후 지체 없이 처리합니다.',
  },
]

export default function PrivacySettings() {
  const navigate = useNavigate()
  const { optionalPrivacyConsent, updateOptionalPrivacyConsent } = useApp()
  const [openSection, setOpenSection] = useState<string | null>('collection')

  return (
    <section className="mx-auto max-w-3xl">
      <button
        type="button"
        onClick={() => navigate('/settings')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 설정으로
      </button>

      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">개인정보 보호</p>
        <h1 className="mt-2 text-3xl font-black">개인정보 처리 안내</h1>
        <p className="mt-2 text-sm leading-7 text-gray-500">
          joopjoop은 맞춤 정책 추천에 필요한 정보만 수집하고 안전하게 관리해요.
        </p>
      </div>

      <div className="mt-7 divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white">
        {privacySections.map((section) => {
          const isOpen = openSection === section.id
          return (
            <div key={section.id}>
              <button
                type="button"
                onClick={() => setOpenSection(isOpen ? null : section.id)}
                className="flex w-full items-center gap-4 px-5 py-5 text-left"
                aria-expanded={isOpen}
              >
                <span className="flex-1 text-sm font-bold text-gray-950">{section.title}</span>
                <ChevronDown
                  size={18}
                  className={`text-gray-400 transition ${isOpen ? 'rotate-180' : ''}`}
                />
              </button>
              {isOpen && (
                <p className="border-t border-gray-100 bg-slate-50 px-5 py-5 text-sm leading-7 text-gray-600">
                  {section.content}
                </p>
              )}
            </div>
          )
        })}
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-black">개인정보 동의 관리</h2>
        <p className="mt-2 text-sm text-gray-500">현재 동의 상태를 확인하거나 철회할 수 있어요.</p>

        <div className="mt-4 divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
          <div className="flex items-start gap-4 p-5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
              <Check size={18} strokeWidth={3} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-bold">서비스 제공을 위한 개인정보 활용</p>
                <span className="text-xs font-semibold text-rose-600">필수</span>
              </div>
              <p className="mt-1 text-xs leading-5 text-gray-500">
                회원 식별과 맞춤 정책 추천 등 핵심 서비스 제공에 사용됩니다.
              </p>
            </div>
            <LockKeyhole size={18} className="mt-1 shrink-0 text-gray-400" />
          </div>

          <div className="flex items-start gap-4 p-5">
            <span
              className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${
                optionalPrivacyConsent ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-400'
              }`}
            >
              <Info size={18} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-bold">추천 품질 개선을 위한 추가 활용</p>
                <span className="text-xs font-semibold text-gray-500">선택</span>
              </div>
              <p className="mt-1 text-xs leading-5 text-gray-500">
                서비스 이용 패턴을 분석해 추천 결과와 사용자 경험을 개선합니다.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={optionalPrivacyConsent}
              aria-label="추천 품질 개선을 위한 추가 활용 동의"
              onClick={() => updateOptionalPrivacyConsent(!optionalPrivacyConsent)}
              className={`relative mt-1 h-7 w-12 shrink-0 rounded-full transition ${
                optionalPrivacyConsent ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition ${
                  optionalPrivacyConsent ? 'left-6' : 'left-1'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-bold text-amber-900">동의 철회 시 영향</p>
          <p className="mt-1 text-xs leading-6 text-amber-800">
            선택 동의를 철회해도 정책 검색과 기본 맞춤 추천은 계속 이용할 수 있지만, 이용 패턴을
            반영한 추천 품질 개선에는 제한이 있을 수 있어요. 필수 동의 철회는 회원 탈퇴를 통해
            처리할 수 있습니다.
          </p>
        </div>
      </div>
    </section>
  )
}
