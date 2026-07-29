import { ArrowLeft, ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const questions = [
  {
    key: 'region',
    title: '현재 거주지역은 어디인가요?',
    hint: '정책마다 지역 기준이 달라요.',
    options: ['서울', '경기', '인천', '부산', '그 외 지역'],
  },
  {
    key: 'housing',
    title: '현재 주거 형태를 알려주세요.',
    hint: '가장 가까운 형태를 골라주세요.',
    options: ['월세', '전세', '자가', '가족과 거주'],
  },
  {
    key: 'income',
    title: '월 소득은 어느 정도인가요?',
    hint: '세전 금액을 기준으로 선택해주세요.',
    options: ['100만 원 이하', '101~200만 원', '201~300만 원', '301만 원 이상'],
  },
]

export default function Onboarding() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const q = questions[step]
  function next() {
    if (step < questions.length - 1) setStep(step + 1)
    else navigate('/')
  }
  return (
    <section className="mx-auto max-w-3xl">
      <div className="flex gap-2">
        {questions.map((_, index) => (
          <span
            key={index}
            className={`h-1.5 flex-1 rounded-full ${index <= step ? 'bg-blue-600' : 'bg-gray-200'}`}
          />
        ))}
      </div>
      <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-10">
        <p className="text-sm font-bold text-blue-600">
          {step + 1} / {questions.length}
        </p>
        <h1 className="mt-5 text-3xl font-black">{q.title}</h1>
        <p className="mt-2 text-sm text-gray-500">{q.hint}</p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {q.options.map((option) => (
            <button
              key={option}
              onClick={() => setAnswers({ ...answers, [q.key]: option })}
              className={`rounded-lg border p-4 text-left font-semibold ${answers[q.key] === option ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 bg-white'}`}
            >
              {option}
            </button>
          ))}
        </div>
        <div className="mt-10 flex justify-between">
          <button
            disabled={step === 0}
            onClick={() => setStep(step - 1)}
            className="inline-flex items-center gap-2 px-3 py-3 text-sm font-semibold text-gray-500 disabled:opacity-30"
          >
            <ArrowLeft size={17} /> 이전
          </button>
          <button
            disabled={!answers[q.key]}
            onClick={next}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-bold text-white disabled:opacity-40"
          >
            {step === questions.length - 1 ? '분석 시작하기' : '다음 질문'} <ArrowRight size={17} />
          </button>
        </div>
      </div>
    </section>
  )
}
