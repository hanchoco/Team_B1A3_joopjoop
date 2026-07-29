import {
  BriefcaseBusiness,
  ChevronDown,
  CreditCard,
  Filter,
  Heart,
  House,
  ReceiptText,
  Star,
  TrainFront,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../../store/useApp'

type PossibilityFilter = 'POSSIBILITY_HIGH' | 'REVIEW_REQUIRED' | 'ALL'
type PolicySort = 'recommended' | 'deadline'

interface PolicyQueryProfile {
  age: number
  region: string
  monthlyIncome: number
  employment: string
  housing: string
}

interface PolicyQuery {
  profile: PolicyQueryProfile
  filter: string
  category: string | null
  sort: PolicySort
}

const policies = [
  {
    id: 'youth-rent',
    title: '청년 월세 한시 특별지원',
    description: '월세 부담이 큰 청년이 조금 더 안정적으로 생활할 수 있도록 주거비를 지원해요.',
    category: '주거',
    possibility: 'POSSIBILITY_HIGH',
    chance: '가능성 높음',
    benefit: '월 최대 20만 원 · 최대 12개월',
    condition: '현재 조건 5개 중 4개 충족',
    matchedConditions: 4,
    totalConditions: 5,
    deadline: 23,
    minAge: 19,
    maxAge: 34,
    regions: ['전국'],
    incomeLimit: 300,
    employments: ['전체'],
    housingTypes: ['월세'],
  },
  {
    id: 'youth-account',
    title: '청년도약계좌',
    description: '청년이 꾸준히 자산을 형성할 수 있도록 정부 기여금과 비과세 혜택을 지원해요.',
    category: '금융',
    possibility: 'POSSIBILITY_HIGH',
    chance: '가능성 높음',
    benefit: '만기 약 5,400만 원 · 정부 기여금 지원',
    condition: '현재 조건 5개 중 5개 충족',
    matchedConditions: 5,
    totalConditions: 5,
    deadline: 51,
    minAge: 19,
    maxAge: 34,
    regions: ['전국'],
    incomeLimit: 750,
    employments: ['전체'],
    housingTypes: ['전체'],
  },
  {
    id: 'transport',
    title: '청년 교통비 지원사업',
    description: '대중교통을 자주 이용하는 청년의 생활비 부담을 덜어드려요.',
    category: '교통',
    possibility: 'REVIEW_REQUIRED',
    chance: '추가 확인 필요',
    benefit: '월 최대 5만 원 · 교통비 환급',
    condition: '현재 조건 5개 중 3개 충족',
    matchedConditions: 3,
    totalConditions: 5,
    deadline: 38,
    minAge: 19,
    maxAge: 34,
    regions: ['서울'],
    incomeLimit: 350,
    employments: ['전체'],
    housingTypes: ['전체'],
  },
  {
    id: 'career-return',
    title: '청년 재직자 경력 지원',
    description: '청년 재직자의 직무 역량 향상과 안정적인 경력 개발을 지원해요.',
    category: '고용',
    possibility: 'REVIEW_REQUIRED',
    chance: '추가 확인 필요',
    benefit: '교육비 최대 100만 원',
    condition: '현재 조건 5개 중 2개 충족',
    matchedConditions: 2,
    totalConditions: 5,
    deadline: 67,
    minAge: 19,
    maxAge: 34,
    regions: ['전국'],
    incomeLimit: 500,
    employments: ['재직 중'],
    housingTypes: ['전체'],
  },
]

const possibilityFilters = [
  { value: 'POSSIBILITY_HIGH', label: '가능성 높음' },
  { value: 'REVIEW_REQUIRED', label: '추가 확인 필요' },
  { value: 'ALL', label: '전체' },
]

const categoryIcons: Record<string, typeof House> = {
  주거: House,
  금융: CreditCard,
  교통: TrainFront,
  고용: BriefcaseBusiness,
  복지: Heart,
  세금: ReceiptText,
}

function queryPolicies({ profile, filter, category, sort }: PolicyQuery) {
  return policies
    .map((policy) => {
      const ageMatch = profile.age >= policy.minAge && profile.age <= policy.maxAge
      const regionMatch = policy.regions.includes('전국') || policy.regions.includes(profile.region)
      const incomeMatch = profile.monthlyIncome <= policy.incomeLimit
      const employmentMatch =
        policy.employments.includes('전체') || policy.employments.includes(profile.employment)
      const housingMatch =
        policy.housingTypes.includes('전체') || policy.housingTypes.includes(profile.housing)
      const allProfileConditionsMatch =
        ageMatch && regionMatch && incomeMatch && employmentMatch && housingMatch
      const allConditionsFulfilled = policy.matchedConditions === policy.totalConditions
      const computedPossibility =
        allProfileConditionsMatch && allConditionsFulfilled ? 'POSSIBILITY_HIGH' : 'REVIEW_REQUIRED'
      const chance = computedPossibility === 'POSSIBILITY_HIGH' ? '가능성 높음' : '추가 확인 필요'
      return { ...policy, possibility: computedPossibility, chance }
    })
    .filter((policy) => {
      const matchesPossibility = filter === 'ALL' || policy.possibility === filter
      const matchesCategory = !category || policy.category === category
      return matchesPossibility && matchesCategory
    })
    .sort((a, b) => {
      if (sort === 'deadline') return a.deadline - b.deadline

      if (a.possibility !== b.possibility) {
        return a.possibility === 'POSSIBILITY_HIGH' ? -1 : 1
      }

      const aConditionRatio = a.matchedConditions / a.totalConditions
      const bConditionRatio = b.matchedConditions / b.totalConditions
      return bConditionRatio - aConditionRatio || a.deadline - b.deadline
    })
}

export default function PolicyList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filterOpen, setFilterOpen] = useState(false)
  const { favoritePolicies, toggleFavorite, userProfile } = useApp()
  const selectedCategory = searchParams.get('category')
  const activeFilter = searchParams.get('filter') || 'POSSIBILITY_HIGH'
  const activeSort: PolicySort =
    searchParams.get('sort') === 'deadline' ? 'deadline' : 'recommended'
  const visiblePolicies = queryPolicies({
    profile: {
      age: userProfile.age,
      region: userProfile.regionName,
      monthlyIncome: userProfile.monthlyIncome,
      employment: userProfile.employment,
      housing: userProfile.housingType,
    },
    filter: activeFilter,
    category: selectedCategory,
    sort: activeSort,
  })

  useEffect(() => {
    if (!searchParams.has('filter')) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.set('filter', 'POSSIBILITY_HIGH')
      setSearchParams(nextParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  function changePossibilityFilter(filter: PossibilityFilter) {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('filter', filter)
    setSearchParams(nextParams)
  }

  return (
    <section>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">
            {selectedCategory ? `${selectedCategory} 추가 답변 반영 완료` : '맞춤 정책 추천'}
          </p>
          <h1 className="mt-2 text-3xl font-black">김나라 님을 위한 정책 12개</h1>
          <p className="mt-2 text-sm text-gray-500">
            {selectedCategory
              ? `${selectedCategory} 분야의 답변을 반영해 추천 정확도를 높였어요.`
              : '가능성이 높은 정책부터 간결하게 모았어요.'}
          </p>
        </div>
        <button
          onClick={() => setFilterOpen(!filterOpen)}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold"
        >
          <Filter size={17} /> 필터 <ChevronDown size={15} />
        </button>
      </div>
      <div className="mt-6 flex gap-2 overflow-x-auto border-b border-gray-200">
        {possibilityFilters.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => changePossibilityFilter(value as PossibilityFilter)}
            className={`shrink-0 border-b-2 px-4 py-3 text-sm font-bold transition ${activeFilter === value ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
          >
            {label}
          </button>
        ))}
      </div>
      {filterOpen && (
        <div className="mt-5 grid gap-5 rounded-xl border border-gray-200 bg-white p-5 sm:grid-cols-2">
          <label className="text-sm font-semibold">
            카테고리
            <select
              defaultValue={selectedCategory || '전체'}
              className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
            >
              <option>전체</option>
              <option>주거</option>
              <option>금융</option>
              <option>교통</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            정렬
            <select
              value={activeSort}
              onChange={(event) => {
                const nextParams = new URLSearchParams(searchParams)
                nextParams.set('sort', event.target.value)
                setSearchParams(nextParams)
              }}
              className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
            >
              <option value="recommended">추천순</option>
              <option value="deadline">마감순</option>
            </select>
          </label>
        </div>
      )}
      <div className="mt-6 space-y-3">
        {visiblePolicies.map((policy) => {
          const { id, title, description, category, chance, benefit, condition, deadline } = policy
          const favorite = Boolean(favoritePolicies[id])
          const CategoryIcon = categoryIcons[category] ?? ReceiptText
          return (
            <article
              key={id}
              className="flex min-h-[250px] flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-blue-300"
            >
              <header className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                  {category}
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${chance.includes('높음') ? 'bg-emerald-100 text-emerald-700' : chance.includes('추가') ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}
                  >
                    {chance}
                  </span>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      toggleFavorite(policy)
                    }}
                    className="rounded-md p-1"
                    aria-label={`${title} ${favorite ? '관심 정책 해제' : '관심 정책 등록'}`}
                  >
                    <Star
                      className={`h-5 w-5 cursor-pointer ${favorite ? 'fill-amber-400 text-amber-400' : 'text-gray-400 hover:text-amber-400'}`}
                    />
                  </button>
                </div>
              </header>

              <div className="mt-4 grid flex-1 grid-cols-[56px_minmax(0,1fr)] gap-4">
                <span className="grid h-14 w-14 place-items-center rounded-lg bg-slate-100 text-gray-500">
                  <CategoryIcon size={27} strokeWidth={1.7} />
                </span>
                <div className="flex min-w-0 flex-col">
                  <div className="flex flex-1 flex-col gap-3">
                    <h2 className="text-xl font-bold text-gray-950">{title}</h2>
                    <p className="text-sm leading-7 text-gray-500">{description}</p>
                    <p className="text-base font-bold leading-7 text-blue-700">{benefit}</p>
                  </div>

                  <footer className="mt-auto flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      <span className="font-semibold text-rose-500">마감 D-{deadline}</span>
                      <span className="h-3 w-px bg-gray-200" />
                      <span className="text-gray-500">{condition}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate(`/policies/${id}`)}
                      className="self-end rounded-lg border border-blue-600 px-4 py-2 text-sm font-medium text-blue-600 transition hover:bg-blue-50"
                    >
                      자세히 보기
                    </button>
                  </footer>
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
