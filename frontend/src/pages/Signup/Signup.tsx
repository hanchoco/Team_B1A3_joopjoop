import { ArrowRight, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { extractErrorMessage } from '../../api/client'
import BrandLogo from '../../components/common/BrandLogo'
import { useApp } from '../../store/useApp'

const consentDetails = {
  terms: {
    title: '서비스 이용약관',
    content: [
      'joopjoop은 청년 정책 검색, 맞춤 추천, 예상 혜택 계산과 정책 Q&A 기능을 제공합니다.',
      '회원은 정확한 정보를 입력하고 계정을 안전하게 관리해야 하며, 서비스를 부정한 목적으로 이용해서는 안 됩니다.',
      '서비스 내용이 변경되거나 운영이 중단되는 경우 관련 내용을 서비스 화면을 통해 안내합니다.',
    ],
  },
  privacy: {
    title: '개인정보 수집·이용 동의',
    content: [
      '수집 항목: 로그인 아이디, 비밀번호, 이름, 출생연도, 거주지역과 사용자가 선택해 입력한 맞춤 정책 정보',
      '이용 목적: 회원 식별, 계정 보호, 맞춤 정책 추천 및 서비스 제공',
      '보유 기간: 회원 탈퇴 시까지 보유하며, 관계 법령상 보존 의무가 있는 정보는 해당 기간 동안 별도 보관합니다.',
      '동의를 거부할 수 있으나, 필수 정보 수집에 동의하지 않으면 회원가입과 서비스 이용이 제한됩니다.',
    ],
  },
} as const

type ConsentDetail = keyof typeof consentDetails

export default function Signup() {
  const navigate = useNavigate()
  const { signup } = useApp()
  const [name, setName] = useState('')
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [termsAgreed, setTermsAgreed] = useState(false)
  const [privacyAgreed, setPrivacyAgreed] = useState(false)
  const [openConsent, setOpenConsent] = useState<ConsentDetail | null>(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password.length < 8) {
      setError('비밀번호는 8자 이상 입력해주세요.')
      return
    }
    if (password !== confirmation) {
      setError('비밀번호 확인 값이 일치하지 않아요.')
      return
    }
    if (!termsAgreed || !privacyAgreed) {
      setError('필수 약관에 동의해주세요.')
      return
    }
    setError('')
    setIsSubmitting(true)
    try {
      await signup({
        email: loginId.trim(),
        password,
        nickname: name.trim(),
        consents: [
          { consent_type: 'TERMS_REQUIRED', consent_version: '1.0', is_agreed: true },
          { consent_type: 'PRIVACY_REQUIRED', consent_version: '1.0', is_agreed: true },
        ],
      })
      navigate('/onboarding')
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="mx-auto max-w-md py-8">
      <div className="text-center">
        <BrandLogo className="mx-auto h-14 w-[205px] object-contain" />
        <h1 className="mt-6 text-2xl font-black">joopjoop 시작하기</h1>
        <p className="mt-2 text-sm text-gray-500">계정을 만들고 내게 맞는 정책을 찾아보세요.</p>
      </div>

      <form
        onSubmit={submit}
        className="mt-7 space-y-5 rounded-xl border border-gray-200 bg-white p-7"
      >
        <label className="block text-sm font-bold">
          이름
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="block text-sm font-bold">
          아이디
          <input
            required
            type="email"
            value={loginId}
            onChange={(event) => setLoginId(event.target.value)}
            autoComplete="username"
            placeholder="이메일 아이디"
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="block text-sm font-bold">
          비밀번호
          <input
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            placeholder="8자 이상 입력"
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="block text-sm font-bold">
          비밀번호 확인
          <input
            required
            type="password"
            value={confirmation}
            onChange={(event) => {
              setConfirmation(event.target.value)
              setError('')
            }}
            autoComplete="new-password"
            placeholder="비밀번호 다시 입력"
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <div className="divide-y divide-gray-200 overflow-hidden rounded-lg bg-slate-50">
          {(
            [
              ['terms', termsAgreed, setTermsAgreed],
              ['privacy', privacyAgreed, setPrivacyAgreed],
            ] as const
          ).map(([id, checked, setChecked]) => {
            const detail = consentDetails[id]
            const isOpen = openConsent === id
            return (
              <div key={id}>
                <div className="flex items-center gap-3 p-4 text-sm">
                  <label className="flex min-w-0 flex-1 items-center gap-3">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) => {
                        setChecked(event.target.checked)
                        setError('')
                      }}
                      className="h-4 w-4 shrink-0 accent-blue-600"
                    />
                    <span>
                      <strong className="font-bold text-blue-600">[필수]</strong> {detail.title}에<br/>
                      동의합니다.
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setOpenConsent(isOpen ? null : id)}
                    className="inline-flex shrink-0 items-center gap-1 text-xs font-bold text-gray-500 hover:text-blue-600"
                    aria-expanded={isOpen}
                  >
                    내용 보기
                    <ChevronDown size={15} className={`transition ${isOpen ? 'rotate-180' : ''}`} />
                  </button>
                </div>
                {isOpen && (
                  <div className="border-t border-gray-200 bg-white px-4 py-4">
                    <h2 className="text-sm font-bold">{detail.title}</h2>
                    <ul className="mt-2 space-y-2 text-xs leading-5 text-gray-600">
                      {detail.content.map((item) => (
                        <li key={item} className="flex gap-2">
                          <span aria-hidden="true">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {error && <p className="text-sm font-semibold text-rose-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3.5 font-bold text-white disabled:opacity-60"
        >
          {isSubmitting ? '가입 중...' : '회원가입 완료'} <ArrowRight size={18} />
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-gray-500">
        이미 계정이 있나요?{' '}
        <button onClick={() => navigate('/login')} className="font-bold text-blue-600">
          로그인
        </button>
      </p>
    </section>
  )
}
