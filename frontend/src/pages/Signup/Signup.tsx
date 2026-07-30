import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { extractErrorMessage } from '../../api/client'
import BrandLogo from '../../components/common/BrandLogo'
import { useApp } from '../../store/useApp'

export default function Signup() {
  const navigate = useNavigate()
  const { signup } = useApp()
  const [name, setName] = useState('')
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [agreed, setAgreed] = useState(false)
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
    if (!agreed) {
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
        <label className="flex items-start gap-3 rounded-lg bg-slate-50 p-4 text-sm">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            className="mt-0.5 h-4 w-4 accent-blue-600"
          />
          <span>
            <strong className="font-bold">[필수]</strong> 서비스 이용약관과 개인정보 수집·이용에
            동의합니다.
          </span>
        </label>
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
