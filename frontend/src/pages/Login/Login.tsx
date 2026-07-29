import { MessageCircle, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import BrandLogo from '../../components/common/BrandLogo'
import { useApp } from '../../store/useApp'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useApp()
  function handleLogin() {
    login()
    navigate('/onboarding')
  }
  return (
    <section className="mx-auto max-w-md pt-10">
      <div className="rounded-xl border border-gray-200 bg-white p-7 text-center">
        <BrandLogo className="mx-auto h-16 w-[230px] object-contain" />
        <p className="mt-5 text-sm leading-7 text-gray-500">
          내게 맞는 청년 정책을 찾고
          <br />
          실제 받을 혜택까지 확인해보세요.
        </p>
        <div className="mt-8 space-y-3">
          <button
            onClick={handleLogin}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#FEE500] py-3.5 font-bold text-[#191919]"
          >
            <MessageCircle size={18} /> 카카오로 시작하기
          </button>
          <button
            onClick={handleLogin}
            className="w-full rounded-lg border border-gray-300 py-3.5 font-bold"
          >
            Google로 계속하기
          </button>
        </div>
        <p className="mt-6 inline-flex items-center gap-1 text-xs text-gray-400">
          <ShieldCheck size={14} /> 개인정보는 안전하게 보호해요.
        </p>
      </div>
    </section>
  )
}
