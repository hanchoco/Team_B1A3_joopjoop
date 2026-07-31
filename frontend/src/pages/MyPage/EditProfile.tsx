import { Camera, CheckCircle2, ChevronDown, UserRound, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getMyProfile } from '../../api/users'
import {
  getCategoryAnswers,
  listCategories,
  listCategoryQuestions,
  saveCategoryAnswers,
} from '../../api/categories'
import { extractErrorMessage } from '../../api/client'
import {
  EMPLOYMENT_STATUS_OPTIONS,
  HOUSEHOLD_TYPE_OPTIONS,
  HOUSING_TYPE_OPTIONS,
  INCOME_BAND_OPTIONS,
  REGION_OPTIONS,
} from '../../constants/profile'
import { useApp } from '../../store/useApp'
import type {
  CategoryAnswerUpsert,
  CategoryQuestionResponse,
  CategoryResponse,
  UserProfileUpdate,
} from '../../types/api'

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

interface QuestionOption {
  label: string
  value: string
}

function parseQuestionOptions(optionsJson: unknown): QuestionOption[] {
  if (!Array.isArray(optionsJson)) return []
  const options: QuestionOption[] = []
  for (const item of optionsJson) {
    if (typeof item === 'string') {
      options.push({ label: item, value: item })
      continue
    }
    if (item && typeof item === 'object' && 'value' in item) {
      const record = item as Record<string, unknown>
      const value = String(record.value)
      const label = typeof record.label === 'string' ? record.label : value
      options.push({ label, value })
    }
  }
  return options
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string')
}

interface CategorySectionState {
  status: 'loading' | 'loaded' | 'error'
  error: string
  questions: CategoryQuestionResponse[]
  answers: Record<number, unknown>
  saving: boolean
  saveError: string
  saved: boolean
}

const answerOptionClass =
  'flex items-center justify-between rounded-lg border px-4 py-2.5 text-left text-sm font-semibold transition'

function answerOptionSelectedClass(selected: boolean): string {
  return selected
    ? `${answerOptionClass} border-blue-600 bg-blue-50 text-blue-700`
    : `${answerOptionClass} border-gray-200 hover:border-blue-300`
}

function CategoryQuestionField({
  question,
  value,
  onChange,
  onToggleMultiOption,
}: {
  question: CategoryQuestionResponse
  value: unknown
  onChange: (value: unknown) => void
  onToggleMultiOption: (option: string) => void
}) {
  const options = parseQuestionOptions(question.options_json)

  return (
    <div>
      <p className="text-sm font-semibold">{question.label}</p>
      {question.description && <p className="mt-1 text-xs text-gray-500">{question.description}</p>}
      <div className="mt-2">
        {question.answer_type === 'BOOLEAN' ? (
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: '예', value: true },
              { label: '아니요', value: false },
            ].map((option) => {
              const selected = value === option.value
              return (
                <button
                  key={option.label}
                  type="button"
                  onClick={() => onChange(option.value)}
                  className={answerOptionSelectedClass(selected)}
                >
                  {option.label}
                  {selected && <CheckCircle2 size={16} />}
                </button>
              )
            })}
          </div>
        ) : question.answer_type === 'NUMBER' ? (
          <input
            type="number"
            value={typeof value === 'number' ? value : ''}
            onChange={(event) =>
              onChange(event.target.value === '' ? undefined : Number(event.target.value))
            }
            placeholder={question.unit ?? undefined}
            className={fieldClass}
          />
        ) : question.answer_type === 'MULTI_SELECT' && options.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {options.map((option) => {
              const selected = asStringArray(value).includes(option.value)
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onToggleMultiOption(option.value)}
                  className={answerOptionSelectedClass(selected)}
                >
                  {option.label}
                  {selected && <CheckCircle2 size={16} />}
                </button>
              )
            })}
          </div>
        ) : options.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {options.map((option) => {
              const selected = value === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onChange(option.value)}
                  className={answerOptionSelectedClass(selected)}
                >
                  {option.label}
                  {selected && <CheckCircle2 size={16} />}
                </button>
              )
            })}
          </div>
        ) : (
          <input
            type="text"
            value={typeof value === 'string' ? value : ''}
            onChange={(event) => onChange(event.target.value)}
            className={fieldClass}
          />
        )}
      </div>
    </div>
  )
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
  const [answerCategories, setAnswerCategories] = useState<CategoryResponse[]>([])
  const [categoriesLoading, setCategoriesLoading] = useState(true)
  const [categoriesError, setCategoriesError] = useState('')
  const [expandedCategoryId, setExpandedCategoryId] = useState<number | null>(null)
  const [sections, setSections] = useState<Record<number, CategorySectionState>>({})

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

  useEffect(() => {
    let cancelled = false
    Promise.resolve()
      .then(() => {
        setCategoriesLoading(true)
        setCategoriesError('')
        return listCategories()
      })
      .then(async (categories) => {
        if (cancelled) return
        const withQuestions = await Promise.all(
          categories.map(async (category) => {
            const questions = await listCategoryQuestions(category.id)
            return questions.length > 0 ? category : null
          }),
        )
        if (cancelled) return
        setAnswerCategories(withQuestions.filter((item): item is CategoryResponse => item !== null))
      })
      .catch((err: unknown) => {
        if (!cancelled) setCategoriesError(extractErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setCategoriesLoading(false)
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

  function toggleCategorySection(categoryId: number) {
    setExpandedCategoryId((current) => (current === categoryId ? null : categoryId))
    const existing = sections[categoryId]
    if (existing) return

    setSections((current) => ({
      ...current,
      [categoryId]: {
        status: 'loading',
        error: '',
        questions: [],
        answers: {},
        saving: false,
        saveError: '',
        saved: false,
      },
    }))
    Promise.all([listCategoryQuestions(categoryId), getCategoryAnswers(categoryId)])
      .then(([questions, answerRecords]) => {
        const answers: Record<number, unknown> = {}
        for (const record of answerRecords) {
          answers[record.question_id] = record.answer_json.value
        }
        setSections((current) => ({
          ...current,
          [categoryId]: {
            status: 'loaded',
            error: '',
            questions,
            answers,
            saving: false,
            saveError: '',
            saved: false,
          },
        }))
      })
      .catch((err: unknown) => {
        setSections((current) => ({
          ...current,
          [categoryId]: {
            status: 'error',
            error: extractErrorMessage(err),
            questions: [],
            answers: {},
            saving: false,
            saveError: '',
            saved: false,
          },
        }))
      })
  }

  function setCategoryAnswerValue(categoryId: number, questionId: number, value: unknown) {
    setSections((current) => {
      const section = current[categoryId]
      if (!section) return current
      const nextAnswers = { ...section.answers }
      if (value === undefined) {
        delete nextAnswers[questionId]
      } else {
        nextAnswers[questionId] = value
      }
      return {
        ...current,
        [categoryId]: { ...section, answers: nextAnswers, saved: false },
      }
    })
  }

  function toggleCategoryMultiOption(categoryId: number, questionId: number, option: string) {
    setSections((current) => {
      const section = current[categoryId]
      if (!section) return current
      const values = asStringArray(section.answers[questionId])
      const nextValues = values.includes(option)
        ? values.filter((item) => item !== option)
        : [...values, option]
      return {
        ...current,
        [categoryId]: {
          ...section,
          answers: { ...section.answers, [questionId]: nextValues },
          saved: false,
        },
      }
    })
  }

  async function saveCategorySection(categoryId: number) {
    const section = sections[categoryId]
    if (!section) return
    setSections((current) => ({
      ...current,
      [categoryId]: { ...current[categoryId], saving: true, saveError: '', saved: false },
    }))
    try {
      const payload: CategoryAnswerUpsert[] = section.questions
        .filter((question) => question.id in section.answers)
        .map((question) => ({
          question_id: question.id,
          answer_json: { value: section.answers[question.id] },
        }))
      const saved = await saveCategoryAnswers(categoryId, payload)
      const nextAnswers = { ...section.answers }
      for (const record of saved) {
        nextAnswers[record.question_id] = record.answer_json.value
      }
      setSections((current) => ({
        ...current,
        [categoryId]: {
          ...current[categoryId],
          answers: nextAnswers,
          saving: false,
          saveError: '',
          saved: true,
        },
      }))
    } catch (err) {
      setSections((current) => ({
        ...current,
        [categoryId]: {
          ...current[categoryId],
          saving: false,
          saveError: extractErrorMessage(err),
        },
      }))
    }
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
          취업 상태
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

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-bold">카테고리별 답변 관리</h2>
        <p className="mt-1 text-sm text-gray-500">
          이전에 저장한 답변을 카테고리별로 확인하고 수정할 수 있어요.
        </p>

        {categoriesLoading ? (
          <p className="mt-6 text-sm text-gray-500">불러오는 중...</p>
        ) : categoriesError ? (
          <p className="mt-6 text-sm font-semibold text-rose-600">{categoriesError}</p>
        ) : answerCategories.length === 0 ? (
          <p className="mt-6 text-sm text-gray-500">추가로 답변할 카테고리가 없어요.</p>
        ) : (
          <div className="mt-6 divide-y divide-gray-100">
            {answerCategories.map((category) => {
              const section = sections[category.id]
              const isExpanded = expandedCategoryId === category.id
              return (
                <div key={category.id} className="py-4">
                  <button
                    type="button"
                    onClick={() => toggleCategorySection(category.id)}
                    className="flex w-full items-center justify-between text-left"
                  >
                    <span className="text-sm font-bold">{category.name}</span>
                    <ChevronDown
                      size={18}
                      className={`text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {isExpanded && (
                    <div className="mt-4">
                      {!section || section.status === 'loading' ? (
                        <p className="text-sm text-gray-500">불러오는 중...</p>
                      ) : section.status === 'error' ? (
                        <p className="text-sm font-semibold text-rose-600">{section.error}</p>
                      ) : section.questions.length === 0 ? (
                        <p className="text-sm text-gray-500">추가 질문이 없어요.</p>
                      ) : (
                        <div className="flex flex-col gap-5">
                          {section.questions.map((question) => (
                            <CategoryQuestionField
                              key={question.id}
                              question={question}
                              value={section.answers[question.id]}
                              onChange={(value) =>
                                setCategoryAnswerValue(category.id, question.id, value)
                              }
                              onToggleMultiOption={(option) =>
                                toggleCategoryMultiOption(category.id, question.id, option)
                              }
                            />
                          ))}
                          {section.saveError && (
                            <p className="text-sm font-semibold text-rose-600">
                              {section.saveError}
                            </p>
                          )}
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              disabled={section.saving || Object.keys(section.answers).length === 0}
                              onClick={() => void saveCategorySection(category.id)}
                              className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {section.saving ? '저장 중...' : '저장'}
                            </button>
                            {section.saved && (
                              <span className="inline-flex items-center gap-1 text-sm font-semibold text-emerald-600">
                                <CheckCircle2 size={16} /> 저장 완료
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
