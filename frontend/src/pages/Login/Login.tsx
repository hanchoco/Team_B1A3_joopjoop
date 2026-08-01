import { ArrowRight, LockKeyhole, UserRound } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { extractErrorMessage } from '../../api/client'
import BrandLogo from '../../components/common/BrandLogo'
import { useApp } from '../../store/useApp'

const EXAMPLE_LOGIN_ID = 'nara@example.com'

function resolveLoginReturnPath(state: unknown): string {
  if (typeof state !== 'object' || state === null || !('returnTo' in state)) return '/'

  const returnTo = (state as { returnTo?: unknown }).returnTo
  return typeof returnTo === 'string' && returnTo.startsWith('/') && !returnTo.startsWith('//')
    ? returnTo
    : '/'
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useApp()
  const [loginId, setLoginId] = useState(EXAMPLE_LOGIN_ID)
  const [isExampleLoginId, setIsExampleLoginId] = useState(true)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(loginId.trim(), password)
      navigate(resolveLoginReturnPath(location.state), { replace: true })
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
        <h1 className="mt-6 text-2xl font-black">다시 만나서 반가워요</h1>
        <p className="mt-2 text-sm text-gray-500">로그인하고 저장한 맞춤 정책을 확인하세요.</p>
      </div>

      <form onSubmit={submit} className="mt-7 rounded-xl border border-gray-200 bg-white p-7">
        <label className="block text-sm font-bold">
          아이디
          <span className="relative mt-2 block">
            <UserRound
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              required
              type="email"
              value={loginId}
              onFocus={(event) => {
                if (isExampleLoginId) {
                  setLoginId('')
                  setIsExampleLoginId(false)
                }
                event.target.setSelectionRange(0, 0)
              }}
              onChange={(event) => {
                setLoginId(event.target.value)
                setIsExampleLoginId(false)
                setError('')
              }}
              autoComplete="username"
              placeholder="이메일 아이디"
              className={`w-full rounded-lg border border-gray-300 py-3.5 pl-11 pr-4 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 ${
                isExampleLoginId ? 'text-gray-400' : 'text-gray-950'
              }`}
            />
          </span>
        </label>
        <label className="mt-5 block text-sm font-bold">
          비밀번호
          <span className="relative mt-2 block">
            <LockKeyhole
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              required
              type="password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setError('')
              }}
              autoComplete="current-password"
              placeholder="비밀번호 입력"
              className="w-full rounded-lg border border-gray-300 py-3.5 pl-11 pr-4 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </span>
        </label>
        {error && <p className="mt-3 text-sm font-semibold text-rose-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3.5 font-bold text-white disabled:opacity-60"
        >
          {isSubmitting ? '로그인 중...' : '로그인'} <ArrowRight size={18} />
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-gray-500">
        아직 계정이 없나요?{' '}
        <button onClick={() => navigate('/signup')} className="font-bold text-blue-600">
          회원가입
        </button>
      </p>
    </section>
  )
}
