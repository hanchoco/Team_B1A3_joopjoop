import { ArrowLeft, ArrowRight, CheckCircle2, Clock3 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

interface CategoryQuestion {
  id: string
  title: string
  description: string
  options: string[]
}

interface CategoryQuestionSet {
  name: string
  questions: CategoryQuestion[]
}

const categoryQuestions: Record<string, CategoryQuestionSet> = {
  housing: {
    name: '주거',
    questions: [
      {
        id: 'rentalType',
        title: '현재 어떤 형태로 거주하고 있나요?',
        description: '계약서에 적힌 임차 형태를 기준으로 골라주세요.',
        options: ['월세', '전세', '반전세', '가족과 거주'],
      },
      {
        id: 'housingCost',
        title: '보증금과 월세는 어느 정도인가요?',
        description: '정확하지 않아도 가장 가까운 구간이면 충분해요.',
        options: [
          '보증금 1천만 원 이하',
          '보증금 1천만~5천만 원',
          '보증금 5천만 원 이상',
          '월세 없음',
        ],
      },
      {
        id: 'homeOwnership',
        title: '현재 본인 명의의 주택이 있나요?',
        description: '분양권과 입주권을 포함해 확인해주세요.',
        options: ['무주택이에요', '주택이 있어요', '잘 모르겠어요'],
      },
    ],
  },
  employment: {
    name: '고용',
    questions: [
      {
        id: 'companySize',
        title: '현재 회사 규모는 어디에 가까운가요?',
        description: '재직 중이 아니라면 해당 항목을 선택해주세요.',
        options: ['중소기업', '중견기업', '대기업', '미취업·구직 중'],
      },
      {
        id: 'employmentType',
        title: '현재 고용 형태를 알려주세요.',
        description: '근로계약서를 기준으로 선택하면 정확해요.',
        options: ['정규직', '계약직', '일용·단기근로', '프리랜서·자영업'],
      },
      {
        id: 'insurance',
        title: '4대 보험에 가입되어 있나요?',
        description: '건강보험 자격득실확인서에서 확인할 수 있어요.',
        options: ['모두 가입', '일부 가입', '미가입', '잘 모르겠어요'],
      },
    ],
  },
  finance: {
    name: '금융',
    questions: [
      {
        id: 'debt',
        title: '현재 갚고 있는 부채나 대출이 있나요?',
        description: '학자금 대출과 카드론도 포함해주세요.',
        options: ['없어요', '1천만 원 이하', '1천만~5천만 원', '5천만 원 이상'],
      },
      {
        id: 'credit',
        title: '최근 신용 관련 어려움이 있었나요?',
        description: '정확한 점수를 몰라도 괜찮아요.',
        options: ['특별한 어려움 없음', '연체 경험 있음', '신용회복 진행 중', '잘 모르겠어요'],
      },
    ],
  },
  welfare: {
    name: '복지',
    questions: [
      {
        id: 'household',
        title: '함께 생활하는 가구원은 몇 명인가요?',
        description: '주민등록등본상 가구원 수를 기준으로 알려주세요.',
        options: ['1인 가구', '2인 가구', '3인 가구', '4인 이상'],
      },
      {
        id: 'care',
        title: '가구 내 돌봄이나 장애 관련 상황이 있나요?',
        description: '해당되는 내용이 없어도 괜찮아요.',
        options: ['해당 없음', '가족 돌봄 중', '장애인 가구원 있음', '둘 다 해당'],
      },
    ],
  },
  transport: {
    name: '교통',
    questions: [
      {
        id: 'transportUse',
        title: '대중교통을 얼마나 자주 이용하나요?',
        description: '평소 한 달 이용 횟수를 떠올려주세요.',
        options: ['주 1~2회', '주 3~4회', '주 5회 이상'],
      },
      {
        id: 'transportCost',
        title: '월평균 교통비는 어느 정도인가요?',
        description: '버스와 지하철 이용 금액을 합쳐주세요.',
        options: ['5만 원 이하', '5만~10만 원', '10만 원 이상'],
      },
    ],
  },
  tax: {
    name: '세금',
    questions: [
      {
        id: 'incomeType',
        title: '주된 소득 형태는 무엇인가요?',
        description: '가장 비중이 큰 소득을 선택해주세요.',
        options: ['근로소득', '사업소득', '프리랜서 소득', '현재 소득 없음'],
      },
      {
        id: 'taxFiling',
        title: '최근 종합소득세 신고를 했나요?',
        description: '기억나지 않으면 확인 필요를 골라도 괜찮아요.',
        options: ['신고했어요', '신고하지 않았어요', '확인이 필요해요'],
      },
    ],
  },
}

export default function CategoryQuestions() {
  const { categoryId } = useParams()
  const navigate = useNavigate()
  const category = categoryQuestions[categoryId ?? 'housing'] ?? categoryQuestions.housing
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const question = category.questions[step]
  const remaining = category.questions.length - step - 1
  const isLast = step === category.questions.length - 1

  function moveNext() {
    if (!isLast) setStep((current) => current + 1)
  }

  function finish() {
    const params = new URLSearchParams({ category: category.name })
    Object.entries(answers).forEach(([key, value]) => params.set(key, value))
    navigate(`/policies?${params.toString()}`)
  }

  return (
    <section className="mx-auto max-w-3xl">
      <button
        type="button"
        onClick={() => (step > 0 ? setStep(step - 1) : navigate('/categories'))}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500"
      >
        <ArrowLeft size={16} /> {step > 0 ? '이전 질문' : '카테고리 선택'}
      </button>

      <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 px-5 py-4">
        <div className="flex items-center gap-3">
          <Clock3 size={19} className="text-blue-600" />
          <div>
            <p className="text-sm font-bold text-blue-800">
              앞으로 {remaining}개의 질문이 남았어요{' '}
              <span className="font-medium text-blue-600">(약 30초 소요)</span>
            </p>
            <p className="mt-1 text-xs text-gray-600">
              답변은 {category.name} 정책의 추천 정확도를 높이는 데만 사용해요.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 flex gap-2">
        {category.questions.map((item, index) => (
          <span
            key={item.id}
            className={`h-1.5 flex-1 rounded-full ${index <= step ? 'bg-blue-600' : 'bg-gray-200'}`}
          />
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-gray-200 bg-white p-6 sm:p-10">
        <p className="text-sm font-bold text-blue-600">
          {category.name} 추가 질문 · {step + 1}/{category.questions.length}
        </p>
        <h1 className="mt-4 text-2xl font-black sm:text-3xl">{question.title}</h1>
        <p className="mt-2 text-sm text-gray-500">{question.description}</p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {question.options.map((option) => {
            const selected = answers[question.id] === option
            return (
              <button
                key={option}
                type="button"
                onClick={() => setAnswers({ ...answers, [question.id]: option })}
                className={`flex min-h-16 items-center justify-between rounded-lg border px-5 py-4 text-left text-sm font-semibold transition ${selected ? 'border-blue-600 bg-blue-50 text-blue-700 ring-2 ring-blue-100' : 'border-gray-200 hover:border-blue-300'}`}
              >
                {option}
                {selected && <CheckCircle2 size={18} />}
              </button>
            )
          })}
        </div>

        <button
          type="button"
          disabled={!answers[question.id]}
          onClick={isLast ? finish : moveNext}
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3.5 font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isLast ? '답변 저장하고 맞춤 정책 보기' : '다음 질문'} <ArrowRight size={18} />
        </button>
      </div>
    </section>
  )
}
