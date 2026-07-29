import { ArrowLeft, CheckCircle2, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

export default function AccountSettings() {
  const navigate = useNavigate()
  const { accountId, updateAccountId } = useApp()
  const [loginId, setLoginId] = useState(accountId)
  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaved(false)

    if (newPassword && newPassword.length < 8) {
      setError('새 비밀번호는 8자 이상 입력해주세요.')
      return
    }
    if (newPassword !== passwordConfirmation) {
      setError('새 비밀번호와 비밀번호 확인 값이 일치하지 않아요.')
      return
    }

    updateAccountId(loginId.trim())
    setNewPassword('')
    setPasswordConfirmation('')
    setError('')
    setSaved(true)
  }

  return (
    <section className="mx-auto max-w-2xl">
      <button
        type="button"
        onClick={() => navigate('/settings')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 설정으로
      </button>

      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">계정 관리</p>
        <h1 className="mt-2 text-3xl font-black">회원 정보</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          로그인 아이디와 비밀번호를 변경할 수 있어요.
        </p>
      </div>

      <form
        onSubmit={submit}
        className="mt-7 rounded-xl border border-gray-200 bg-white p-6 sm:p-8"
      >
        <label className="block text-sm font-bold">
          아이디
          <input
            required
            type="email"
            value={loginId}
            onChange={(event) => setLoginId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </label>

        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <label className="block text-sm font-bold">
            새 비밀번호
            <span className="relative mt-2 block">
              <input
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="8자 이상 입력"
                autoComplete="new-password"
                className="w-full rounded-lg border border-gray-300 px-4 py-3.5 pr-11 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
          <label className="block text-sm font-bold">
            새 비밀번호 확인
            <input
              type={showPassword ? 'text' : 'password'}
              value={passwordConfirmation}
              onChange={(event) => setPasswordConfirmation(event.target.value)}
              placeholder="새 비밀번호 다시 입력"
              autoComplete="new-password"
              className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
        </div>

        <p className="mt-3 text-xs leading-5 text-gray-500">
          비밀번호를 변경하지 않으려면 두 입력란을 비워두세요.
        </p>

        {error && <p className="mt-4 text-sm font-semibold text-rose-600">{error}</p>}
        {saved && (
          <p className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-emerald-700">
            <CheckCircle2 size={17} /> 회원 정보가 변경됐어요.
          </p>
        )}

        <button
          type="submit"
          className="mt-7 w-full rounded-lg bg-blue-600 py-3.5 font-bold text-white hover:bg-blue-700"
        >
          변경하기
        </button>
      </form>
    </section>
  )
}
