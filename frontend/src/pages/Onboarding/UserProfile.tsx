import { ArrowLeft, ArrowRight, Heart, MessageCircleMore } from 'lucide-react'
import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const fieldClass =
  'mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-3.5 text-gray-800 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

export default function UserProfile() {
  const navigate = useNavigate()
  const { saveUserProfile, userProfile } = useApp()
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    age: String(userProfile.age),
    regionName: userProfile.regionName,
    housingType: userProfile.housingType,
    monthlyIncome: String(userProfile.monthlyIncome),
    concern: userProfile.concern,
  })

  function updateField(
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    try {
      await saveUserProfile(
        {
          ...form,
          age: Number(form.age),
          birthYear: new Date().getFullYear() - Number(form.age),
          monthlyIncome: Number(form.monthlyIncome),
        },
        true,
      )
      navigate('/policies?filter=ELIGIBLE', {
        state: { profileSaved: true },
      })
    } catch {
      setError('정보를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section className="mx-auto max-w-2xl">
      <div className="mb-5">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700">
          <Heart size={13} fill="currentColor" /> 맞춤 분석 1단계
        </span>
        <h1 className="mt-4 text-3xl font-black">지금의 나를 알려주세요</h1>
        <p className="mt-2 text-sm leading-7 text-gray-500">
          입력한 정보는 다음 화면의 맞춤 정책 추천에 바로 반영해드려요.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8"
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="block text-sm font-bold">
            나이
            <input
              required
              name="age"
              value={form.age}
              onChange={updateField}
              type="number"
              min="19"
              max="34"
              className={fieldClass}
            />
          </label>
          <label className="block text-sm font-bold">
            거주 지역
            <select
              required
              name="regionName"
              value={form.regionName}
              onChange={updateField}
              className={fieldClass}
            >
              <option>서울</option>
              <option>경기</option>
              <option>인천</option>
              <option>부산</option>
              <option>대구</option>
              <option>광주</option>
              <option>대전</option>
              <option>그 외 지역</option>
            </select>
          </label>
          <label className="block text-sm font-bold">
            주거 형태
            <select
              required
              name="housingType"
              value={form.housingType}
              onChange={updateField}
              className={fieldClass}
            >
              <option>월세</option>
              <option>전세</option>
              <option>자가</option>
              <option>가족과 함께 거주</option>
            </select>
          </label>
          <label className="block text-sm font-bold">
            월 소득
            <div className="relative">
              <input
                required
                name="monthlyIncome"
                value={form.monthlyIncome}
                onChange={updateField}
                type="number"
                min="0"
                step="10"
                className={`${fieldClass} pr-16`}
              />
              <span className="absolute bottom-3.5 right-4 text-sm text-gray-500">만 원</span>
            </div>
          </label>
        </div>
        <label className="mt-5 block text-sm font-bold">
          요즘 가장 큰 고민 한 줄
          <div className="relative">
            <MessageCircleMore size={18} className="absolute left-4 top-[25px] text-blue-500" />
            <textarea
              name="concern"
              value={form.concern}
              onChange={updateField}
              rows={3}
              placeholder="예: 월세가 부담돼서 저축을 시작하기 어려워요."
              className={`${fieldClass} resize-none pl-11`}
            />
          </div>
        </label>
        {error && <p className="mt-4 text-sm font-semibold text-rose-600">{error}</p>}
        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="inline-flex items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-bold text-gray-500 hover:bg-slate-50"
          >
            <ArrowLeft size={16} /> 이전으로
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3.5 font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {isSaving ? '저장하고 있어요...' : '다음으로 · 맞춤 정책 보기'} <ArrowRight size={18} />
          </button>
        </div>
      </form>
    </section>
  )
}
