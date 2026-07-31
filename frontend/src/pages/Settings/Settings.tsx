import { Bell, CalendarClock, ChevronRight, KeyRound, Mail, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const menuItems = [
  { id: 'notifications', label: '알림 설정', icon: Bell },
  { id: 'account', label: '비밀번호 변경', icon: KeyRound },
  { id: 'privacy', label: '개인정보 처리 안내', icon: ShieldCheck },
  { id: 'logout', label: '로그아웃' },
  { id: 'withdraw', label: '회원 탈퇴' },
]

const detailContent = {
  notifications: {
    title: '알림 설정',
    body: '관심 정책으로 저장한 전체 공고의 마감 일정을 알려드려요.',
  },
}

type DetailKey = keyof typeof detailContent
type MenuId = DetailKey | 'account' | 'privacy' | 'logout' | 'withdraw'
type DetailContent = (typeof detailContent)[DetailKey]

interface NotificationSwitchProps {
  checked: boolean
  disabled?: boolean
  label: string
  onChange: (checked: boolean) => void
}

function NotificationSwitch({
  checked,
  disabled = false,
  label,
  onChange,
}: NotificationSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-7 w-12 shrink-0 rounded-full transition ${
        checked ? 'bg-blue-600' : 'bg-gray-300'
      } disabled:cursor-not-allowed disabled:opacity-45`}
    >
      <span
        className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition ${
          checked ? 'left-6' : 'left-1'
        }`}
      />
    </button>
  )
}

export default function Settings() {
  const navigate = useNavigate()
  const { logout, notificationSettings, updateNotificationSettings } = useApp()
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
    if (id === 'account') {
      navigate('/settings/account')
      return
    }
    if (id === 'privacy') {
      navigate('/settings/privacy')
      return
    }
    setDetail(detailContent[id])
  }

  function toggleAllNotifications(enabled: boolean) {
    updateNotificationSettings({
      ...notificationSettings,
      enabled,
    })
  }

  function toggleSchedule(
    schedule: 'sevenDaysBefore' | 'threeDaysBefore' | 'deadlineDay',
    checked: boolean,
  ) {
    updateNotificationSettings({
      ...notificationSettings,
      [schedule]: checked,
    })
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
          <div className="max-h-[calc(100vh-2rem)] w-full max-w-lg overflow-y-auto rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
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
              <>
                <div className="mt-5 flex items-center justify-between border-y border-gray-200 py-5">
                  <div>
                    <p className="font-bold text-gray-950">전체 마감 알림</p>
                    <p className="mt-1 text-xs leading-5 text-gray-500">
                      관심 정책 전체의 마감 알림을 한 번에 관리해요.
                    </p>
                  </div>
                  <NotificationSwitch
                    checked={notificationSettings.enabled}
                    label="전체 마감 알림"
                    onChange={toggleAllNotifications}
                  />
                </div>

                <div className="mt-5 flex items-center gap-3 rounded-lg bg-slate-50 px-4 py-3">
                  <Mail size={18} className="text-blue-600" />
                  <div>
                    <p className="text-sm font-semibold text-gray-950">이메일로 알려드려요</p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      등록된 계정 이메일로 마감 알림을 보내드려요.
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <div className="flex items-center gap-2">
                    <CalendarClock size={18} className="text-blue-600" />
                    <h3 className="text-sm font-bold text-gray-950">알림 시점</h3>
                  </div>
                  <div className="mt-3 divide-y divide-gray-100 rounded-lg border border-gray-200">
                    {[
                      {
                        key: 'sevenDaysBefore' as const,
                        label: '마감 7일 전',
                      },
                      {
                        key: 'threeDaysBefore' as const,
                        label: '마감 3일 전',
                      },
                      {
                        key: 'deadlineDay' as const,
                        label: '마감 당일',
                      },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center gap-3 px-4 py-3.5">
                        <span className="flex-1 text-sm font-semibold">{label}</span>
                        <NotificationSwitch
                          checked={notificationSettings[key]}
                          disabled={!notificationSettings.enabled}
                          label={`${label} 이메일 알림`}
                          onChange={(checked) => toggleSchedule(key, checked)}
                        />
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-xs leading-5 text-gray-500">
                    전체 알림을 켠 뒤 이메일을 받을 시점을 선택할 수 있어요.
                  </p>
                </div>
              </>
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
