import { ArrowLeft, Bot, LoaderCircle, Send, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../../store/useApp'

const recommendedQuestions = [
  '신청 자격이 조금 궁금해요.',
  '필요한 서류가 무엇인가요?',
  '신청 결과는 언제 나오나요?',
]

const answerMap: Record<string, string> = {
  '신청 자격이 조금 궁금해요.':
    '연령, 소득, 주거 조건을 중심으로 확인해요. 현재 입력하신 정보로는 주요 조건을 충족하지만, 최종 자격은 신청 기관의 심사를 통해 확정돼요.',
  '필요한 서류가 무엇인가요?':
    '임대차계약서 사본, 최근 월세 이체 내역, 가족관계증명서를 먼저 준비해 주세요. 공고에 따라 추가 서류가 필요할 수 있어요.',
  '신청 결과는 언제 나오나요?':
    '접수 후 소득·재산 조사를 거쳐 보통 4~6주 정도 걸려요. 신청 기관의 처리 상황에 따라 조금 달라질 수 있어요.',
}

const greeting = '안녕하세요, 김나라 님. 청년 월세 지원 정책에 대해 무엇이든 편하게 물어보세요.'

interface ChatMessage {
  role: 'assistant' | 'user'
  text: string
  showSuggestions?: boolean
}

export default function Chatbot() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { userProfile } = useApp()
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(true)
  const [isAnswering, setIsAnswering] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      text: greeting.replace('김나라', userProfile?.name || '김나라'),
    },
  ])

  useEffect(() => {
    const area = scrollAreaRef.current
    if (area) area.scrollTo({ top: area.scrollHeight, behavior: 'smooth' })
  }, [messages, isAnswering, showSuggestions])

  useEffect(() => () => clearTimeout(timerRef.current), [])

  function ask(question: string) {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isAnswering) return

    setShowSuggestions(false)
    setIsAnswering(true)
    setInput('')
    setMessages((current) => [...current, { role: 'user', text: trimmedQuestion }])

    timerRef.current = setTimeout(() => {
      const answer =
        answerMap[trimmedQuestion] ||
        '질문을 확인했어요. 저장된 프로필과 현재 정책 공고를 기준으로 차근차근 안내해 드릴게요.'

      setMessages((current) => [
        ...current,
        { role: 'assistant', text: answer },
        {
          role: 'assistant',
          text: greeting.replace('김나라', userProfile?.name || '김나라'),
          showSuggestions: true,
        },
      ])
      setIsAnswering(false)
      setShowSuggestions(true)
    }, 650)
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    ask(input)
  }

  return (
    <section className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={() => navigate(`/policies/${id}`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 정책 상세로
      </button>

      <div className="mt-5">
        <p className="text-sm font-semibold text-blue-600">정책 전용 도우미</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight">AI에게 물어보기</h1>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          궁금한 내용을 편하게 질문하면 현재 정책을 기준으로 쉽게 설명해 드릴게요.
        </p>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div
          ref={scrollAreaRef}
          className="h-[460px] space-y-5 overflow-y-auto bg-slate-50/60 p-5 sm:p-7"
          aria-live="polite"
        >
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`}>
              <div className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>
                {message.role === 'assistant' && (
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-100 text-blue-600">
                    <Bot size={18} />
                  </span>
                )}
                <p
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-7 ${
                    message.role === 'user'
                      ? 'rounded-tr-md bg-blue-600 text-white'
                      : 'rounded-tl-md border border-blue-100 bg-white text-gray-700 shadow-sm'
                  }`}
                >
                  {message.text}
                </p>
                {message.role === 'user' && (
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gray-200 text-gray-600">
                    <UserRound size={18} />
                  </span>
                )}
              </div>

              {message.showSuggestions && showSuggestions && index === messages.length - 1 && (
                <div className="ml-12 mt-3 flex flex-wrap gap-2">
                  {recommendedQuestions.map((question) => (
                    <button
                      type="button"
                      key={question}
                      onClick={() => ask(question)}
                      className="rounded-full border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {isAnswering && (
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-blue-100 text-blue-600">
                <Bot size={18} />
              </span>
              <span className="inline-flex items-center gap-2 rounded-2xl rounded-tl-md border border-blue-100 bg-white px-4 py-3 text-sm text-gray-500">
                <LoaderCircle size={16} className="animate-spin text-blue-500" />
                답변을 정리하고 있어요
              </span>
            </div>
          )}

          {showSuggestions && messages.length === 1 && (
            <div className="ml-12 flex flex-wrap gap-2">
              {recommendedQuestions.map((question) => (
                <button
                  type="button"
                  key={question}
                  onClick={() => ask(question)}
                  className="rounded-full border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
                >
                  {question}
                </button>
              ))}
            </div>
          )}
        </div>

        <form onSubmit={submit} className="flex gap-3 border-t border-gray-100 p-4">
          <label htmlFor="ai-question" className="sr-only">
            정책 질문 입력
          </label>
          <input
            id="ai-question"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={isAnswering}
            className="min-w-0 flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm outline-none placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50"
            placeholder="궁금한 정책 내용을 입력해 주세요."
          />
          <button
            type="submit"
            disabled={isAnswering || !input.trim()}
            className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            aria-label="질문 보내기"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </section>
  )
}
