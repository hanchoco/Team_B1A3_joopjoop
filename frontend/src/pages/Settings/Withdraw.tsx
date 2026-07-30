import { AlertTriangle, ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAuthErrorMessage } from '../../api/auth'
import { withdrawCurrentAccount } from '../../api/users'
import { useApp } from '../../store/useApp'

export default function Withdraw() {
  const navigate = useNavigate()
  const { logout } = useApp()
  const [agreed, setAgreed] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function withdraw(): Promise<void> {
    if (!agreed) {
      setError('탈퇴 안내를 확인하고 동의해 주세요.')
      return
    }
    if (currentPassword.length < 8) {
      setError('현재 비밀번호를 입력해 주세요.')
      return
    }

    setIsSubmitting(true)
    setError('')
    try {
      await withdrawCurrentAccount(currentPassword)
      logout()
      navigate('/login', { replace: true })
    } catch (requestError: unknown) {
      setError(
        getAuthErrorMessage(
          requestError,
          '회원 탈퇴를 완료하지 못했어요. 현재 비밀번호를 다시 확인해 주세요.',
        ),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="mx-auto max-w-2xl">
      <button
        type="button"
        onClick={() => navigate('/settings')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> 설정으로
      </button>
      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
        <span className="grid h-11 w-11 place-items-center rounded-full bg-rose-100 text-rose-600">
          <AlertTriangle size={21} />
        </span>
        <h1 className="mt-5 text-2xl font-black">회원 탈퇴 안내</h1>
        <p className="mt-3 text-sm leading-7 text-gray-600">
          탈퇴하면 저장한 맞춤 정보와 관심 정책, 신청 준비 기록을 다시 복구할 수 없어요. 신중하게
          확인해주세요.
        </p>
        <label className="mt-6 block text-sm font-bold">
          현재 비밀번호
          <input
            type="password"
            value={currentPassword}
            onChange={(event) => {
              setCurrentPassword(event.target.value)
              setError('')
            }}
            autoComplete="current-password"
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-100"
          />
        </label>
        <label className="mt-6 flex items-start gap-3 rounded-lg bg-slate-50 p-4 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(event) => {
              setAgreed(event.target.checked)
              setError('')
            }}
            className="mt-1 h-4 w-4 accent-blue-600"
          />
          안내 사항을 모두 확인했으며 회원 탈퇴에 동의합니다.
        </label>
        {error && <p className="mt-4 text-sm font-semibold text-rose-600">{error}</p>}
        <div className="mt-6 grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="rounded-lg border border-gray-300 py-3 text-sm font-bold"
          >
            취소
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void withdraw()}
            className="rounded-lg bg-rose-600 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:bg-rose-300"
          >
            {isSubmitting ? '탈퇴 처리 중...' : '회원 탈퇴'}
          </button>
        </div>
      </div>
    </section>
  )
}
