import { ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/useApp'
import type { UserProfileUpdate } from '../../types'

type ProfileQuestionKey =
  'birthYear' | 'regionName' | 'incomeBracket' | 'employment' | 'householdType' | 'housingType'

interface ProfileQuestion {
  key: ProfileQuestionKey
  title: string
  hint: string
  options?: string[]
}

const questions: ProfileQuestion[] = [
  {
    key: 'birthYear',
    title: '출생연도를 알려주세요.',
    hint: '연령 조건이 있는 정책을 확인하는 데 사용해요.',
  },
  {
    key: 'regionName',
    title: '현재 거주지역은 어디인가요?',
    hint: '지역별로 신청할 수 있는 정책이 달라요.',
    options: ['서울', '경기', '인천', '부산', '대구', '광주', '대전', '그 외 지역'],
  },
  {
    key: 'incomeBracket',
    title: '현재 소득구간을 알려주세요.',
    hint: '정확한 금액 대신 가장 가까운 구간을 선택해주세요.',
    options: ['월 100만 원 이하', '월 101~200만 원', '월 201~300만 원', '월 301만 원 이상'],
  },
  {
    key: 'employment',
    title: '현재 취업상태를 알려주세요.',
    hint: '재직 여부와 고용 형태에 맞는 정책을 찾을게요.',
    options: ['재직 중', '구직 중', '학생', '프리랜서·자영업'],
  },
  {
    key: 'householdType',
    title: '현재 가구형태를 알려주세요.',
    hint: '가구원 기준이 있는 정책을 확인하는 데 사용해요.',
    options: ['1인 가구', '부모와 거주', '부부 가구', '자녀가 있는 가구', '기타'],
  },
  {
    key: 'housingType',
    title: '현재 주거형태를 알려주세요.',
    hint: '가장 가까운 형태를 선택해주세요.',
    options: ['월세', '전세', '자가', '공공임대', '기숙사·시설'],
  },
]

const incomeValues: Record<string, number> = {
  '월 100만 원 이하': 100,
  '월 101~200만 원': 200,
  '월 201~300만 원': 300,
  '월 301만 원 이상': 400,
}

export default function Onboarding() {
  const navigate = useNavigate()
  const { saveUserProfile, updateUserProfile } = useApp()
  const [step, setStep] = useState(0)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [answers, setAnswers] = useState<Record<ProfileQuestionKey, string>>({
    birthYear: '',
    regionName: '',
    incomeBracket: '',
    employment: '',
    householdType: '',
    housingType: '',
  })
  const question = questions[step]
  const selectedValue = answers[question.key]
  const isLast = step === questions.length - 1

  function saveAnswer(value: string) {
    setAnswers((current) => ({ ...current, [question.key]: value }))

    const update: UserProfileUpdate = { [question.key]: value }
    if (question.key === 'birthYear') update.birthYear = Number(value)
    if (question.key === 'incomeBracket') update.monthlyIncome = incomeValues[value]
    updateUserProfile(update)
  }

  async function next() {
    if (!selectedValue) return
    if (!isLast) {
      setStep((current) => current + 1)
      return
    }

    setIsSaving(true)
    setError('')
    try {
      await saveUserProfile(
        {
          birthYear: Number(answers.birthYear),
          regionName: answers.regionName,
          incomeBracket: answers.incomeBracket,
          monthlyIncome: incomeValues[answers.incomeBracket],
          employment: answers.employment,
          householdType: answers.householdType,
          housingType: answers.housingType,
        },
        true,
      )
      navigate('/')
    } catch {
      setError('정보를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setIsSaving(false)
    }
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

        {question.key === 'birthYear' ? (
          <label className="mt-8 block max-w-sm text-sm font-bold">
            출생연도
            <input
              autoFocus
              type="number"
              min={1950}
              max={new Date().getFullYear()}
              value={selectedValue}
              onChange={(event) => saveAnswer(event.target.value)}
              placeholder="예: 2000"
              className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3.5 text-base font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </label>
        ) : (
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {question.options?.map((option) => {
              const selected = selectedValue === option
              return (
                <button
                  type="button"
                  key={option}
                  onClick={() => saveAnswer(option)}
                  className={`flex min-h-16 items-center justify-between rounded-lg border p-4 text-left font-semibold ${
                    selected
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white hover:border-blue-300'
                  }`}
                >
                  {option}
                  {selected && <CheckCircle2 size={18} />}
                </button>
              )
            })}
          </div>
        )}

        <p className="mt-6 text-xs leading-5 text-gray-400">
          입력을 완료하면 안전하게 저장되며 마이페이지에서 변경할 수 있어요.
        </p>
        {error && <p className="mt-3 text-sm font-semibold text-rose-600">{error}</p>}
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
            disabled={!selectedValue || isSaving}
            onClick={() => void next()}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-bold text-white disabled:opacity-40"
          >
            {isSaving ? '저장하고 있어요...' : isLast ? '입력 완료' : '다음'}{' '}
            <ArrowRight size={17} />
          </button>
        </div>
      </div>
    </section>
  )
}
