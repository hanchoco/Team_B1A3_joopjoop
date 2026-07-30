import { ArrowRight, Bot, Send, Sparkles, TrendingDown, UserRound } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import mockData from '../../utils/mockData.json'

const recommendedQuestions = ['필요한 서류가 무엇인가요?']

const mockAnswers: Record<string, string> = {
  '필요한 서류가 무엇인가요?':
    '임대차계약서 사본, 최근 월세 이체 내역, 가족관계증명서를 먼저 준비하면 좋아요. 신청 전 최신 공고도 함께 확인해드릴게요.',
}

function formatManWon(amount: number) {
  return `${new Intl.NumberFormat('ko-KR').format(amount / 10000)}만 원`
}

export default function ImpactView() {
  const { savingsSimulation, userProfile } = mockData
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<{ role: 'assistant' | 'user'; text: string }[]>([
    {
      role: 'assistant',
      text: `${userProfile.name} 님의 상황을 기준으로 계산했어요. 궁금한 내용을 편하게 물어보세요.`,
    },
  ])

  function selectQuestion(question: string) {
    setInput(question)
  }

  function sendQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const question = input.trim()
    if (!question) return
    setMessages((current) => [
      ...current,
      { role: 'user', text: question },
      {
        role: 'assistant',
        text:
          mockAnswers[question] ||
          '질문을 확인했어요. 현재 입력하신 프로필과 정책 공고를 기준으로 차근차근 안내해드릴게요.',
      },
    ])
    setInput('')
  }

  return (
    <section className="mx-auto max-w-4xl">
      <div className="text-center">
        <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3.5 py-2 text-xs font-bold text-emerald-700">
          <Sparkles size={14} /> 나의 예상 혜택
        </span>
        <h1 className="mt-4 text-3xl font-black tracking-tight text-gray-950">
          지원받으면 생활비가 이렇게 달라져요
        </h1>
        <p className="mt-2 text-sm leading-7 text-gray-500">
          입력해주신 월세와 예상 지원 금액을 바탕으로 계산했어요.
        </p>
      </div>

      <div className="mt-7 rounded-2xl border border-blue-100 bg-white p-5 shadow-sm sm:p-7">
        <div className="grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr]">
          <article className="rounded-xl border border-rose-100 bg-rose-50 p-6">
            <p className="text-xs font-bold text-rose-600">BEFORE · 지원 전</p>
            <p className="mt-5 text-sm text-gray-600">월 주거비</p>
            <p className="mt-1 text-4xl font-black tracking-tight text-gray-950">
              {formatManWon(savingsSimulation.before.housingCost)}
            </p>
            <div className="mt-6 h-2.5 overflow-hidden rounded-full bg-white">
              <div className="h-full w-full rounded-full bg-rose-300" />
            </div>
          </article>

          <div className="grid place-items-center">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-blue-600 text-white shadow-sm">
              <ArrowRight size={19} className="rotate-90 md:rotate-0" />
            </span>
          </div>

          <article className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 to-emerald-50 p-6">
            <p className="text-xs font-bold text-blue-700">AFTER · 지원 후</p>
            <p className="mt-5 text-sm text-gray-600">월 주거비</p>
            <p className="mt-1 text-4xl font-black tracking-tight text-blue-700">
              {formatManWon(savingsSimulation.after.housingCost)}
            </p>
            <div className="mt-6 h-2.5 overflow-hidden rounded-full bg-white/80">
              <div className="h-full w-2/3 rounded-full bg-blue-500" />
            </div>
          </article>
        </div>

        <div className="mt-4 flex flex-col items-center justify-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-center sm:flex-row">
          <TrendingDown size={20} className="text-amber-700" />
          <p className="text-sm font-semibold text-amber-800">
            1년이면 총{' '}
            <strong className="text-xl font-black">
              {formatManWon(savingsSimulation.annualSavings)}
            </strong>
            을 아낄 수 있어요!
          </p>
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-600">
              <Bot size={21} />
            </span>
            <div>
              <h2 className="font-black text-gray-950">AI 정책 도우미</h2>
              <p className="mt-0.5 text-xs text-gray-500">
                어려운 정책 내용도 다정하고 쉽게 설명해드릴게요.
              </p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {recommendedQuestions.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => selectQuestion(question)}
                className="rounded-full border border-blue-100 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
              >
                {question}
              </button>
            ))}
          </div>
        </div>

        <div className="h-72 space-y-4 overflow-y-auto bg-slate-50/60 p-5 sm:p-6">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
            >
              {message.role === 'assistant' && (
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue-100 text-blue-600">
                  <Bot size={16} />
                </span>
              )}
              <p
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'rounded-tr-md bg-blue-600 text-white' : 'rounded-tl-md bg-white text-gray-700 shadow-sm'}`}
              >
                {message.text}
              </p>
              {message.role === 'user' && (
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gray-200 text-gray-500">
                  <UserRound size={16} />
                </span>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={sendQuestion} className="flex gap-2 border-t border-gray-100 p-4">
          <label htmlFor="impact-question" className="sr-only">
            AI 정책 질문
          </label>
          <input
            id="impact-question"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="추천 질문을 누르거나 궁금한 내용을 입력해주세요."
            className="min-w-0 flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm outline-none placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
          <button
            type="submit"
            className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700"
            aria-label="질문 보내기"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </section>
  )
}
