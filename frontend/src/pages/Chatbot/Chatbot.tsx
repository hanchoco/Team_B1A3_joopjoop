import { ArrowLeft, Bot, LoaderCircle, Send, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { askPolicyQuestion } from '../../api/chatbot'
import { extractErrorMessage } from '../../api/client'
import { useApp } from '../../store/useApp'
import { isPolicyDetailReturnNavigationState } from '../../utils/policyNavigation'

interface ChatMessage {
  role: 'assistant' | 'user'
  text: string
}

const INITIAL_SUGGESTED_QUESTIONS = [
  '제가 이 정책에 지원할 수 있나요?',
  '필요한 서류는 무엇인가요?',
  '소득 기준은 어떻게 계산하나요?',
  '신청 절차가 궁금합니다.',
]

export default function Chatbot() {
  const navigate = useNavigate()
  const location = useLocation()
  const { id } = useParams()
  const policyId = Number(id)
  const navigationState = isPolicyDetailReturnNavigationState(location.state)
    ? location.state
    : null
  const policyDetailReturnTo = navigationState?.policyDetailReturnTo ?? `/policies/${id}`
  const { currentUser } = useApp()
  const displayName = currentUser?.nickname || currentUser?.email.split('@')[0] || '회원'
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState('')
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>(
    INITIAL_SUGGESTED_QUESTIONS,
  )
  const [isAnswering, setIsAnswering] = useState(false)
  const [error, setError] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      text: `안녕하세요, ${displayName} 님. 이 정책에 대해 무엇이든 편하게 물어보세요.`,
    },
  ])

  useEffect(() => {
    const area = scrollAreaRef.current
    if (area) area.scrollTo({ top: area.scrollHeight, behavior: 'smooth' })
  }, [messages, isAnswering])

  async function ask(question: string) {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isAnswering || !Number.isFinite(policyId)) return

    setSuggestedQuestions([])
    setError('')
    setInput('')
    setMessages((current) => [...current, { role: 'user', text: trimmedQuestion }])
    setIsAnswering(true)
    try {
      const data = await askPolicyQuestion(policyId, trimmedQuestion)
      setMessages((current) => [...current, { role: 'assistant', text: data.answer }])
      setSuggestedQuestions(data.suggested_questions)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsAnswering(false)
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void ask(input)
  }

  function returnToPolicyDetail() {
    navigate(policyDetailReturnTo, { state: navigationState?.policyDetailState })
  }

  if (!Number.isFinite(policyId)) {
    return (
      <section className="mx-auto max-w-4xl">
        <button
          onClick={() => navigate('/policies')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
        >
          <ArrowLeft size={16} /> 정책 목록으로
        </button>
        <p className="mt-6 rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-600">
          올바르지 않은 정책입니다.
        </p>
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-4xl">
      <button
        type="button"
        onClick={returnToPolicyDetail}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-blue-600"
      >
        <ArrowLeft size={16} /> 정책 상세
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
            <div
              key={`${message.role}-${index}`}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
            >
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

          {!isAnswering && suggestedQuestions.length > 0 && (
            <div className="ml-12 flex flex-wrap gap-2">
              {suggestedQuestions.map((question) => (
                <button
                  type="button"
                  key={question}
                  onClick={() => void ask(question)}
                  className="rounded-full border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
                >
                  {question}
                </button>
              ))}
            </div>
          )}
        </div>

        {error && (
          <p className="border-t border-rose-100 bg-rose-50 px-5 py-3 text-sm font-semibold text-rose-600">
            {error}
          </p>
        )}

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
