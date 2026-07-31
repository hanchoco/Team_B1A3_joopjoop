import { ArrowLeft, AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { withdrawAccount } from '../../api/users'
import { extractErrorMessage } from '../../api/client'
import { useApp } from '../../store/useApp'

export default function Withdraw() {
  const navigate = useNavigate()
  const { logout } = useApp()
  const [agreed, setAgreed] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submitWithdraw() {
    if (!agreed) {
      setError('안내 사항 확인 및 탈퇴 동의가 필요해요.')
      return
    }
    if (!password) {
      setError('비밀번호를 입력해주세요.')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      await withdrawAccount({
        current_password: password,
        confirm_withdrawal: true,
      })
      logout()
      navigate('/login')
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
        <label className="mt-5 block text-sm font-bold">
          비밀번호 확인
          <input
            type="password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value)
              setError('')
            }}
            autoComplete="current-password"
            placeholder="비밀번호 입력"
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
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
            disabled={submitting}
            onClick={() => void submitWithdraw()}
            className="rounded-lg bg-rose-600 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? '처리 중...' : '회원 탈퇴'}
          </button>
        </div>
      </div>
    </section>
  )
}
