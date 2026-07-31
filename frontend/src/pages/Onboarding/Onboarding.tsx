import { ArrowLeft, ArrowRight, CheckCircle2, ChevronDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  EMPLOYMENT_STATUS_OPTIONS,
  HOUSEHOLD_TYPE_OPTIONS,
  HOUSING_TYPE_OPTIONS,
  INCOME_BAND_OPTIONS,
  REGION_OPTIONS,
} from '../../constants/profile'
import { extractErrorMessage } from '../../api/client'
import { useApp } from '../../store/useApp'
import type { UserProfileUpdate } from '../../types/api'

type FieldKey =
  | 'birth_year'
  | 'region_code'
  | 'income_band_code'
  | 'employment_status_code'
  | 'household_type_code'
  | 'housing_type_code'

interface Question {
  key: FieldKey
  title: string
  hint: string
  options?: { value: string; label: string }[]
}

const NO_REGION_CODE = '__none__'
const MIN_BIRTH_YEAR = 1950
const CURRENT_YEAR = new Date().getFullYear()
const DEFAULT_YEAR_SCROLL_POSITION = 2007
const BIRTH_YEARS = Array.from(
  { length: CURRENT_YEAR - MIN_BIRTH_YEAR + 1 },
  (_, index) => CURRENT_YEAR - index,
)

const questions: Question[] = [
  {
    key: 'birth_year',
    title: '출생연도를 알려주세요.',
    hint: '연령 조건이 있는 정책을 확인하는 데 사용해요.',
  },
  {
    key: 'region_code',
    title: '현재 거주지역은 어디인가요?',
    hint: '지역별로 신청할 수 있는 정책이 달라요.',
    options: REGION_OPTIONS.map((option) => ({
      value: option.code ?? NO_REGION_CODE,
      label: option.name,
    })),
  },
  {
    key: 'income_band_code',
    title: '중위소득 대비 소득 수준을 알려주세요.',
    hint: '정확한 금액 대신 가장 가까운 구간을 선택해주세요.',
    options: INCOME_BAND_OPTIONS.map((option) => ({ value: option.code, label: option.label })),
  },
  {
    key: 'employment_status_code',
    title: '현재 취업상태를 알려주세요.',
    hint: '재직 여부와 고용 형태에 맞는 정책을 찾을게요.',
    options: EMPLOYMENT_STATUS_OPTIONS.map((option) => ({
      value: option.code,
      label: option.label,
    })),
  },
  {
    key: 'household_type_code',
    title: '현재 가구형태를 알려주세요.',
    hint: '가구원 기준이 있는 정책을 확인하는 데 사용해요.',
    options: HOUSEHOLD_TYPE_OPTIONS.map((option) => ({ value: option.code, label: option.label })),
  },
  {
    key: 'housing_type_code',
    title: '현재 주거형태를 알려주세요.',
    hint: '가장 가까운 형태를 선택해주세요.',
    options: HOUSING_TYPE_OPTIONS.map((option) => ({ value: option.code, label: option.label })),
  },
]

export default function Onboarding() {
  const navigate = useNavigate()
  const { updateProfile } = useApp()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<FieldKey, string>>({
    birth_year: '',
    region_code: '',
    income_band_code: '',
    employment_status_code: '',
    household_type_code: '',
    housing_type_code: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [yearListOpen, setYearListOpen] = useState(false)
  const yearListRef = useRef<HTMLDivElement>(null)
  const defaultYearRef = useRef<HTMLButtonElement>(null)
  const question = questions[step]
  const selectedValue = answers[question.key]
  const isLast = step === questions.length - 1

  useEffect(() => {
    if (yearListOpen && yearListRef.current && defaultYearRef.current) {
      yearListRef.current.scrollTop = defaultYearRef.current.offsetTop
    }
  }, [yearListOpen])

  function saveAnswer(value: string) {
    setAnswers((current) => ({ ...current, [question.key]: value }))
  }

  async function finish() {
    setSubmitting(true)
    setError('')
    try {
      const payload: UserProfileUpdate = {
        birth_year: Number(answers.birth_year),
        region_code: answers.region_code === NO_REGION_CODE ? null : answers.region_code,
        income_band_code: answers.income_band_code as UserProfileUpdate['income_band_code'],
        employment_status_code:
          answers.employment_status_code as UserProfileUpdate['employment_status_code'],
        household_type_code:
          answers.household_type_code as UserProfileUpdate['household_type_code'],
        housing_type_code: answers.housing_type_code as UserProfileUpdate['housing_type_code'],
        onboarding_completed: true,
      }
      await updateProfile(payload)
      navigate('/')
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  function next() {
    if (!selectedValue) return
    if (isLast) void finish()
    else setStep((current) => current + 1)
  }

  return (
    <section className="mx-auto max-w-3xl">
      <div className="flex gap-2">
        {questions.map((item, index) => (
          <span
            key={item.key}
            className={`h-1.5 flex-1 rounded-full ${index <= step ? 'bg-blue-600' : 'bg-gray-200'}`}
          />
        ))}
      </div>

      <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-10">
        <p className="text-sm font-bold text-blue-600">
          기본 정보 {step + 1} / {questions.length}
        </p>
        <h1 className="mt-5 text-3xl font-black">{question.title}</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">{question.hint}</p>

        {question.key === 'birth_year' ? (
          <div className="mt-8 max-w-sm text-sm font-bold">
            출생연도
            <div className="relative mt-2">
              <input
                autoFocus
                type="number"
                min={MIN_BIRTH_YEAR}
                max={CURRENT_YEAR}
                value={selectedValue}
                onChange={(event) => saveAnswer(event.target.value)}
                placeholder="예: 2000"
                aria-label="출생연도 직접 입력"
                className="w-full rounded-lg border border-gray-300 py-3.5 pl-4 pr-12 text-base font-normal outline-none [appearance:textfield] focus:border-blue-500 focus:ring-2 focus:ring-blue-100 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <button
                type="button"
                onClick={() => setYearListOpen((current) => !current)}
                className="absolute right-0 top-0 grid h-full w-12 place-items-center text-gray-500"
                aria-label="출생연도 목록 열기"
                aria-expanded={yearListOpen}
              >
                <ChevronDown
                  size={19}
                  className={`transition ${yearListOpen ? 'rotate-180' : ''}`}
                />
              </button>
              {yearListOpen && (
                <div
                  ref={yearListRef}
                  className="absolute z-20 mt-2 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white p-1 shadow-lg"
                >
                  {BIRTH_YEARS.map((year) => {
                    const selected = selectedValue === String(year)
                    return (
                      <button
                        key={year}
                        ref={year === DEFAULT_YEAR_SCROLL_POSITION ? defaultYearRef : undefined}
                        type="button"
                        onClick={() => {
                          saveAnswer(String(year))
                          setYearListOpen(false)
                        }}
                        className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-normal ${
                          selected
                            ? 'bg-blue-50 font-bold text-blue-700'
                            : 'text-gray-700 hover:bg-slate-50'
                        }`}
                      >
                        {year}년{selected && <CheckCircle2 size={16} />}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {question.options?.map((option) => {
              const selected = selectedValue === option.value
              return (
                <button
                  type="button"
                  key={option.value}
                  onClick={() => saveAnswer(option.value)}
                  className={`flex min-h-16 items-center justify-between rounded-lg border p-4 text-left font-semibold ${
                    selected
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white hover:border-blue-300'
                  }`}
                >
                  {option.label}
                  {selected && <CheckCircle2 size={18} />}
                </button>
              )
            })}
          </div>
        )}

        <p className="mt-6 text-xs leading-5 text-gray-400">
          선택한 정보는 마지막 단계에서 저장되며 마이페이지에서 변경할 수 있어요.
        </p>
        {error && <p className="mt-4 text-sm font-semibold text-rose-600">{error}</p>}
        <div className="mt-8 flex justify-between">
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep((current) => current - 1)}
            className="inline-flex items-center gap-2 px-3 py-3 text-sm font-semibold text-gray-500 disabled:opacity-30"
          >
            <ArrowLeft size={17} /> 이전
          </button>
          <button
            type="button"
            disabled={!selectedValue || submitting}
            onClick={next}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-bold text-white disabled:opacity-40"
          >
            {isLast ? (submitting ? '저장 중...' : '입력 완료') : '다음'} <ArrowRight size={17} />
          </button>
        </div>
      </div>
    </section>
  )
}
