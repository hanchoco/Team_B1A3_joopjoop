import { Camera, UserRound, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getMyProfile } from '../../api/users'
import { extractErrorMessage } from '../../api/client'
import {
  EMPLOYMENT_STATUS_OPTIONS,
  HOUSEHOLD_TYPE_OPTIONS,
  HOUSING_TYPE_OPTIONS,
  INCOME_BAND_OPTIONS,
  REGION_OPTIONS,
} from '../../constants/profile'
import { useApp } from '../../store/useApp'
import type { UserProfileUpdate } from '../../types/api'

const fieldClass =
  'mt-2 w-full rounded-lg border border-gray-300 bg-white p-3 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

const NO_REGION_CODE = '__none__'
const EMPTY = ''

const emptyForm = {
  birth_year: EMPTY,
  region_code: EMPTY,
  income_band_code: EMPTY,
  employment_status_code: EMPTY,
  household_type_code: EMPTY,
  housing_type_code: EMPTY,
}

export default function EditProfile() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { updateProfile, avatarUrl, updateAvatarUrl } = useApp()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [nextAvatarUrl, setNextAvatarUrl] = useState(avatarUrl)
  const [avatarError, setAvatarError] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        setLoading(true)
        setError('')
        return getMyProfile()
      })
      .then((data) => {
        if (cancelled) return
        setForm({
          birth_year: data.birth_year ? String(data.birth_year) : EMPTY,
          region_code: data.region_code ?? NO_REGION_CODE,
          income_band_code: data.income_band_code ?? EMPTY,
          employment_status_code: data.employment_status_code ?? EMPTY,
          household_type_code: data.household_type_code ?? EMPTY,
          housing_type_code: data.housing_type_code ?? EMPTY,
        })
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(extractErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const payload: UserProfileUpdate = {
        birth_year: form.birth_year ? Number(form.birth_year) : null,
        region_code: form.region_code === NO_REGION_CODE ? null : form.region_code || null,
        income_band_code: (form.income_band_code || null) as UserProfileUpdate['income_band_code'],
        employment_status_code: (form.employment_status_code ||
          null) as UserProfileUpdate['employment_status_code'],
        household_type_code: (form.household_type_code ||
          null) as UserProfileUpdate['household_type_code'],
        housing_type_code: (form.housing_type_code ||
          null) as UserProfileUpdate['housing_type_code'],
      }
      await updateProfile(payload)
      updateAvatarUrl(nextAvatarUrl)
      navigate(searchParams.get('from') === 'home' ? '/' : '/mypage')
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  function changeAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setAvatarError('이미지 파일만 선택할 수 있어요.')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setAvatarError('2MB 이하의 이미지를 선택해 주세요.')
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setNextAvatarUrl(reader.result)
        setAvatarError('')
      }
    }
    reader.onerror = () => setAvatarError('이미지를 불러오지 못했어요. 다시 선택해 주세요.')
    reader.readAsDataURL(file)
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-gray-500">불러오는 중...</p>
  }

  return (
    <section className="mx-auto max-w-2xl">
      <p className="text-sm font-semibold text-blue-600">마이페이지</p>
      <h1 className="mt-2 text-3xl font-black">내 정보 수정</h1>
      <p className="mt-2 text-sm text-gray-500">
        변경된 정보는 앞으로의 정책 추천과 조건 확인에 반영돼요.
      </p>
      <form
        onSubmit={(event) => void submit(event)}
        className="mt-6 grid gap-5 rounded-xl border border-gray-200 bg-white p-6 sm:grid-cols-2"
      >
        <div className="flex items-center gap-5 border-b border-gray-100 pb-5 sm:col-span-2">
          <span className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-full bg-slate-100 text-gray-400">
            {nextAvatarUrl ? (
              <img
                src={nextAvatarUrl}
                alt="프로필 사진 미리보기"
                className="h-full w-full object-cover"
              />
            ) : (
              <UserRound size={36} />
            )}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-bold">프로필 사진</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-sm font-semibold text-blue-700"
              >
                <Camera size={16} /> 사진 변경
              </button>
              {nextAvatarUrl && (
                <button
                  type="button"
                  onClick={() => {
                    setNextAvatarUrl(undefined)
                    setAvatarError('')
                  }}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold text-gray-600"
                >
                  <X size={16} /> 기본 이미지
                </button>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={changeAvatar}
              className="sr-only"
            />
            <p className={`mt-2 text-xs ${avatarError ? 'text-red-600' : 'text-gray-500'}`}>
              {avatarError || 'JPG, PNG 등 이미지 파일을 2MB까지 등록할 수 있어요.'}
            </p>
          </div>
        </div>
        <label className="block text-sm font-semibold">
          출생연도
          <input
            type="number"
            min={1950}
            max={new Date().getFullYear()}
            value={form.birth_year}
            onChange={(event) => setForm({ ...form, birth_year: event.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="block text-sm font-semibold">
          거주지역
          <select
            value={form.region_code}
            onChange={(event) => setForm({ ...form, region_code: event.target.value })}
            className={fieldClass}
          >
            {REGION_OPTIONS.map((option) => (
              <option key={option.name} value={option.code ?? NO_REGION_CODE}>
                {option.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          소득구간
          <select
            value={form.income_band_code}
            onChange={(event) => setForm({ ...form, income_band_code: event.target.value })}
            className={fieldClass}
          >
            <option value={EMPTY}>선택 안 함</option>
            {INCOME_BAND_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          취업상태
          <select
            value={form.employment_status_code}
            onChange={(event) => setForm({ ...form, employment_status_code: event.target.value })}
            className={fieldClass}
          >
            <option value={EMPTY}>선택 안 함</option>
            {EMPLOYMENT_STATUS_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          가구형태
          <select
            value={form.household_type_code}
            onChange={(event) => setForm({ ...form, household_type_code: event.target.value })}
            className={fieldClass}
          >
            <option value={EMPTY}>선택 안 함</option>
            {HOUSEHOLD_TYPE_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          주거형태
          <select
            value={form.housing_type_code}
            onChange={(event) => setForm({ ...form, housing_type_code: event.target.value })}
            className={fieldClass}
          >
            <option value={EMPTY}>선택 안 함</option>
            {HOUSING_TYPE_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        {error && <p className="text-sm font-semibold text-rose-600 sm:col-span-2">{error}</p>}
        <button
          disabled={submitting}
          className="w-full rounded-lg bg-blue-600 py-3.5 font-bold text-white disabled:opacity-60 sm:col-span-2"
        >
          {submitting ? '저장 중...' : '저장하기'}
        </button>
      </form>
    </section>
  )
}
