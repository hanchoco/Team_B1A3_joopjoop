import { CircleUserRound, Menu, Settings as SettingsIcon } from 'lucide-react'
import { BrowserRouter, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import BrandLogo from '../components/common/BrandLogo'
import Chatbot from '../pages/Chatbot/Chatbot'
import Checklist from '../pages/Checklist/Checklist'
import CategoryQuestions from '../pages/CategorySelect/CategoryQuestions'
import CategorySelect from '../pages/CategorySelect/CategorySelect'
import Dashboard from '../pages/Dashboard/Dashboard'
import Login from '../pages/Login/Login'
import Signup from '../pages/Signup/Signup'
import EditProfile from '../pages/MyPage/EditProfile'
import MyPage from '../pages/MyPage/MyPage'
import MyPolicies from '../pages/MyPolicies/MyPolicies'
import Onboarding from '../pages/Onboarding/Onboarding'
import UserProfile from '../pages/Onboarding/UserProfile'
import PolicyDetail from '../pages/PolicyDetail/PolicyDetail'
import PolicyList from '../pages/PolicyList/PolicyList'
import ImpactView from '../pages/Simulator/ImpactView'
import Simulator from '../pages/Simulator/Simulator'
import Settings from '../pages/Settings/Settings'
import AccountSettings from '../pages/Settings/AccountSettings'
import PrivacySettings from '../pages/Settings/PrivacySettings'
import Withdraw from '../pages/Settings/Withdraw'
import { useApp } from '../store/useApp'
import RequireAuth from './RequireAuth'

function AppLayout() {
  const navigate = useNavigate()
  const { isLoggedIn } = useApp()
  const menu = [
    ['홈', '/'],
    ['카테고리', '/categories'],
    ['맞춤 정책', '/policies?filter=ALL'],
    ['마이페이지', '/mypage'],
  ]
  return (
    <div className="min-h-screen bg-slate-50 text-gray-950">
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-5 sm:px-8">
          <button onClick={() => navigate('/')} aria-label="joopjoop 홈으로 이동">
            <BrandLogo className="h-8 w-[116px] object-contain" />
          </button>
          <nav className="ml-auto hidden items-center gap-7 md:flex">
            {menu.slice(0, 3).map(([label, path]) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                className={({ isActive }) =>
                  `text-sm font-semibold ${isActive ? 'text-blue-600' : 'text-gray-500 hover:text-gray-950'}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-6 flex items-center gap-4 text-gray-500">
            {isLoggedIn ? (
              <>
                <button onClick={() => navigate('/settings')} aria-label="설정">
                  <SettingsIcon size={19} />
                </button>
                <button
                  onClick={() => navigate('/mypage')}
                  className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-600"
                  aria-label="마이페이지"
                >
                  <CircleUserRound size={20} />
                  <span className="hidden sm:inline">마이페이지</span>
                </button>
              </>
            ) : (
              <button
                onClick={() => navigate('/login')}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white"
              >
                로그인
              </button>
            )}
            <button className="md:hidden" aria-label="메뉴">
              <Menu size={20} />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8 sm:py-10">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/onboarding"
            element={
              <RequireAuth>
                <Onboarding />
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <UserProfile />
              </RequireAuth>
            }
          />
          <Route path="/" element={<Dashboard />} />
          <Route path="/categories" element={<CategorySelect />} />
          <Route
            path="/categories/:categoryId/questions"
            element={
              <RequireAuth>
                <CategoryQuestions />
              </RequireAuth>
            }
          />
          <Route
            path="/policies"
            element={
              <RequireAuth>
                <PolicyList />
              </RequireAuth>
            }
          />
          <Route
            path="/policies/:id"
            element={
              <RequireAuth>
                <PolicyDetail />
              </RequireAuth>
            }
          />
          <Route
            path="/policies/:id/simulation"
            element={
              <RequireAuth>
                <Simulator />
              </RequireAuth>
            }
          />
          <Route path="/policies/:id/impact" element={<ImpactView />} />
          <Route path="/impact" element={<ImpactView />} />
          <Route
            path="/policies/:id/prepare"
            element={
              <RequireAuth>
                <Checklist />
              </RequireAuth>
            }
          />
          <Route
            path="/policies/:id/ai-chat"
            element={
              <RequireAuth>
                <Chatbot />
              </RequireAuth>
            }
          />
          <Route
            path="/mypage"
            element={
              <RequireAuth>
                <MyPage />
              </RequireAuth>
            }
          />
          <Route
            path="/mypage/policies"
            element={
              <RequireAuth>
                <MyPolicies />
              </RequireAuth>
            }
          />
          <Route
            path="/mypage/profile"
            element={
              <RequireAuth>
                <EditProfile />
              </RequireAuth>
            }
          />
          <Route
            path="/settings"
            element={
              <RequireAuth>
                <Settings />
              </RequireAuth>
            }
          />
          <Route
            path="/settings/account"
            element={
              <RequireAuth>
                <AccountSettings />
              </RequireAuth>
            }
          />
          <Route
            path="/settings/privacy"
            element={
              <RequireAuth>
                <PrivacySettings />
              </RequireAuth>
            }
          />
          <Route
            path="/settings/withdraw"
            element={
              <RequireAuth>
                <Withdraw />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
