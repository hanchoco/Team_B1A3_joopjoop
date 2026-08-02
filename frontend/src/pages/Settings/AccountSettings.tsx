import { ArrowLeft, CheckCircle2, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { changePassword } from '../../api/users'
import { extractErrorMessage } from '../../api/client'
import ConfirmModal from '../../components/common/ConfirmModal'

export default function AccountSettings() {
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successOpen, setSuccessOpen] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (newPassword.length < 8) {
      setError('새 비밀번호는 8자 이상 입력해주세요.')
      return
    }
    if (newPassword !== passwordConfirmation) {
      setError('새 비밀번호와 비밀번호 확인 값이 일치하지 않아요.')
      return
    }

    setSubmitting(true)
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: passwordConfirmation,
      })
      setCurrentPassword('')
      setNewPassword('')
      setPasswordConfirmation('')
      setSuccessOpen(true)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
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
        <h1 className="mt-2 text-3xl font-black">비밀번호 변경</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          현재 비밀번호를 확인한 뒤 새 비밀번호로 변경할 수 있어요.
        </p>
      </div>

      <form
        onSubmit={(event) => void submit(event)}
        className="mt-7 rounded-xl border border-gray-200 bg-white p-6 sm:p-8"
      >
        <label className="block text-sm font-bold">
          현재 비밀번호
          <span className="relative mt-2 block">
            <input
              required
              type={showPassword ? 'text' : 'password'}
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              placeholder="현재 비밀번호 입력"
              autoComplete="current-password"
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

        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <label className="block text-sm font-bold">
            새 비밀번호
            <input
              required
              type={showPassword ? 'text' : 'password'}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="8자 이상 입력"
              autoComplete="new-password"
              className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <label className="block text-sm font-bold">
            새 비밀번호 확인
            <input
              required
              type={showPassword ? 'text' : 'password'}
              value={passwordConfirmation}
              onChange={(event) => setPasswordConfirmation(event.target.value)}
              placeholder="새 비밀번호 다시 입력"
              autoComplete="new-password"
              className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
        </div>

        {error && <p className="mt-4 text-sm font-semibold text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="mt-7 w-full rounded-lg bg-blue-600 py-3.5 font-bold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? '변경 중...' : '변경하기'}
        </button>
      </form>

      {successOpen && (
        <ConfirmModal
          title="비밀번호가 변경됐어요."
          icon={
            <span className="grid h-11 w-11 place-items-center rounded-full bg-emerald-100 text-emerald-600">
              <CheckCircle2 size={21} />
            </span>
          }
          confirmLabel="확인"
          onConfirm={() => {
            setSuccessOpen(false)
            navigate('/settings')
          }}
        />
      )}
    </section>
  )
}
