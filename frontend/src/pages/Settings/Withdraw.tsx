import { ArrowLeft, AlertTriangle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Withdraw() {
  const navigate = useNavigate()
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
          <input type="checkbox" className="mt-1 h-4 w-4 accent-blue-600" />
          안내 사항을 모두 확인했으며 회원 탈퇴에 동의합니다.
        </label>
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
            className="rounded-lg bg-rose-600 py-3 text-sm font-bold text-white"
          >
            회원 탈퇴
          </button>
        </div>
      </div>
    </section>
  )
}
