import type {
  CategoryAnswerResponse,
  CategoryQuestionResponse,
  UserProfileResponse,
} from '../types/api'
import { filterVisibleCategoryQuestions, hasUsableAnswerValue } from './categoryQuestions'

const PROFILE_ACCURACY_FIELDS = [
  'birth_year',
  'region_code',
  'income_band_code',
  'employment_status_code',
  'household_type_code',
  'housing_type_code',
] as const

export interface CategoryAccuracyData {
  categoryCode: string
  questions: CategoryQuestionResponse[]
  answers: CategoryAnswerResponse[]
}

export function calculateProfileAccuracy(
  profile: UserProfileResponse,
  categoryData: CategoryAccuracyData[],
): number {
  const values: unknown[] = PROFILE_ACCURACY_FIELDS.map((field) => profile[field])

  for (const { categoryCode, questions, answers } of categoryData) {
    const answerByQuestionId = new Map(
      answers.map((answer) => [answer.question_id, answer.answer_json.value]),
    )
    const matchingQuestions = filterVisibleCategoryQuestions(questions, categoryCode).filter(
      (question) => question.is_active && question.is_used_for_matching,
    )

    for (const question of matchingQuestions) {
      values.push(answerByQuestionId.get(question.id))
    }
  }

  const completedCount = values.filter(hasUsableAnswerValue).length
  return values.length === 0 ? 0 : Math.round((completedCount / values.length) * 100)
}
