import { Bell, ChevronRight, ShieldCheck, UserRound, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const menuItems = [
  { id: 'notifications', label: '알림 설정', icon: Bell },
  { id: 'account', label: '회원 정보', icon: UserRound },
  { id: 'privacy', label: '개인정보 처리 안내', icon: ShieldCheck },
  { id: 'logout', label: '로그아웃' },
  { id: 'withdraw', label: '회원 탈퇴' },
]

const detailContent = {
  notifications: {
    title: '알림 설정',
    body: '중요한 정책 마감일과 신청 진행 상황을 놓치지 않도록 알려드릴게요.',
  },
  account: {
    title: '회원 정보',
    body: '김나라 님 · nara@example.com\n가입한 계정과 기본 회원 정보를 확인할 수 있어요.',
  },
  privacy: {
    title: '개인정보 처리 안내',
    body: '입력하신 정보는 맞춤 정책 추천과 신청 준비를 돕는 목적으로만 안전하게 사용해요.',
  },
}

type DetailKey = keyof typeof detailContent
type MenuId = DetailKey | 'logout' | 'withdraw'
type DetailContent = (typeof detailContent)[DetailKey]

export default function Settings() {
  const navigate = useNavigate()
  const { logout } = useApp()
  const [detail, setDetail] = useState<DetailContent | null>(null)
  const [logoutOpen, setLogoutOpen] = useState(false)

  function handleMenu(id: MenuId) {
    if (id === 'logout') {
      setLogoutOpen(true)
      return
    }
    if (id === 'withdraw') {
      navigate('/settings/withdraw')
      return
    }
    setDetail(detailContent[id])
  }

  return (
    <section className="mx-auto max-w-2xl">
      <p className="text-sm font-semibold text-blue-600">마이페이지</p>
      <h1 className="mt-2 text-3xl font-black">설정</h1>
      <p className="mt-2 text-sm text-gray-500">계정과 서비스 이용 설정을 관리할 수 있어요.</p>

      <div className="mt-7 overflow-hidden rounded-xl border border-gray-200 bg-white">
        {menuItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => handleMenu(id as MenuId)}
            className="flex w-full items-center gap-3 border-b border-gray-100 px-5 py-5 text-left text-sm font-semibold text-gray-950 transition last:border-b-0 hover:bg-slate-50"
          >
            {Icon && <Icon size={18} className="text-gray-400" />}
            <span className="flex-1">{label}</span>
            <ChevronRight size={18} className="text-gray-400" />
          </button>
        ))}
      </div>

      {detail && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-gray-950/35 px-5"
          role="dialog"
          aria-modal="true"
          aria-labelledby="detail-title"
        >
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-blue-600">설정 안내</p>
                <h2 id="detail-title" className="mt-1 text-xl font-black">
                  {detail.title}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setDetail(null)}
                className="grid h-9 w-9 place-items-center rounded-lg text-gray-400 hover:bg-slate-100"
                aria-label="닫기"
              >
                <X size={19} />
              </button>
            </div>
            <p className="mt-5 whitespace-pre-line text-sm leading-7 text-gray-600">
              {detail.body}
            </p>
            {detail.title === '알림 설정' && (
              <label className="mt-5 flex items-center justify-between rounded-lg bg-slate-50 p-4 text-sm font-semibold">
                정책 마감 알림
                <input type="checkbox" defaultChecked className="h-5 w-5 accent-blue-600" />
              </label>
            )}
            <button
              type="button"
              onClick={() => setDetail(null)}
              className="mt-6 w-full rounded-lg bg-blue-600 py-3 text-sm font-bold text-white"
            >
              확인
            </button>
          </div>
        </div>
      )}

      {logoutOpen && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-gray-950/35 px-5"
          role="dialog"
          aria-modal="true"
          aria-labelledby="logout-title"
        >
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 text-center shadow-xl">
            <h2 id="logout-title" className="text-xl font-black">
              정말 로그아웃하시겠습니까?
            </h2>
            <p className="mt-2 text-sm leading-6 text-gray-500">
              다시 이용하려면 로그인이 필요해요.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setLogoutOpen(false)}
                className="rounded-lg border border-gray-300 bg-white py-3 text-sm font-bold text-gray-700"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
                className="rounded-lg bg-blue-600 py-3 text-sm font-bold text-white"
              >
                로그아웃
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
