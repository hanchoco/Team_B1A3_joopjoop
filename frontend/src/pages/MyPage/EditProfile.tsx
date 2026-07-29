import { Camera, UserRound, X } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const fieldClass =
  'mt-2 w-full rounded-lg border border-gray-300 bg-white p-3 font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

export default function EditProfile() {
  const navigate = useNavigate()
  const { userProfile, updateUserProfile } = useApp()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [avatarUrl, setAvatarUrl] = useState(userProfile.avatarUrl)
  const [avatarError, setAvatarError] = useState('')
  const [form, setForm] = useState({
    birthYear: String(userProfile.birthYear),
    regionName: userProfile.regionName,
    incomeBracket: userProfile.incomeBracket,
    employment: userProfile.employment,
    householdType: userProfile.householdType,
    housingType: userProfile.housingType,
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    updateUserProfile({
      ...form,
      birthYear: Number(form.birthYear),
      avatarUrl,
    })
    navigate('/mypage')
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
        setAvatarUrl(reader.result)
        setAvatarError('')
      }
    }
    reader.onerror = () => setAvatarError('이미지를 불러오지 못했어요. 다시 선택해 주세요.')
    reader.readAsDataURL(file)
  }

  return (
    <section className="mx-auto max-w-2xl">
      <p className="text-sm font-semibold text-blue-600">마이페이지</p>
      <h1 className="mt-2 text-3xl font-black">내 정보 수정</h1>
      <p className="mt-2 text-sm text-gray-500">
        변경된 정보는 앞으로의 정책 추천과 조건 확인에 반영돼요.
      </p>
      <form
        onSubmit={submit}
        className="mt-6 grid gap-5 rounded-xl border border-gray-200 bg-white p-6 sm:grid-cols-2"
      >
        <div className="flex items-center gap-5 border-b border-gray-100 pb-5 sm:col-span-2">
          <span className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-full bg-slate-100 text-gray-400">
            {avatarUrl ? (
              <img
                src={avatarUrl}
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
              {avatarUrl && (
                <button
                  type="button"
                  onClick={() => {
                    setAvatarUrl(undefined)
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
            required
            type="number"
            value={form.birthYear}
            onChange={(event) => setForm({ ...form, birthYear: event.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="block text-sm font-semibold">
          거주지역
          <select
            value={form.regionName}
            onChange={(event) => setForm({ ...form, regionName: event.target.value })}
            className={fieldClass}
          >
            {['서울', '경기', '인천', '부산', '대구', '광주', '대전', '그 외 지역'].map(
              (option) => (
                <option key={option}>{option}</option>
              ),
            )}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          소득구간
          <select
            value={form.incomeBracket}
            onChange={(event) => setForm({ ...form, incomeBracket: event.target.value })}
            className={fieldClass}
          >
            {['월 100만 원 이하', '월 101~200만 원', '월 201~300만 원', '월 301만 원 이상'].map(
              (option) => (
                <option key={option}>{option}</option>
              ),
            )}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          취업상태
          <select
            value={form.employment}
            onChange={(event) => setForm({ ...form, employment: event.target.value })}
            className={fieldClass}
          >
            {['재직 중', '구직 중', '학생', '프리랜서·자영업'].map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          가구형태
          <select
            value={form.householdType}
            onChange={(event) => setForm({ ...form, householdType: event.target.value })}
            className={fieldClass}
          >
            {['1인 가구', '부모와 거주', '부부 가구', '자녀가 있는 가구', '기타'].map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-semibold">
          주거형태
          <select
            value={form.housingType}
            onChange={(event) => setForm({ ...form, housingType: event.target.value })}
            className={fieldClass}
          >
            {['월세', '전세', '자가', '공공임대', '기숙사·시설'].map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </label>
        <button className="w-full rounded-lg bg-blue-600 py-3.5 font-bold text-white sm:col-span-2">
          저장하기
        </button>
      </form>
    </section>
  )
}
