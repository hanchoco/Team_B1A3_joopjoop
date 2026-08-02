import type { CategoryQuestionResponse } from '../types/api'
import { LEGACY_EMPLOYMENT_COMPANY_SIZE_QUESTION_KEY } from '../constants/categoryQuestions'

export const HIDDEN_QUESTION_KEYS = new Set(['finance.total_debt_amount'])

const UNCERTAIN_ANSWER_VALUES = new Set(['unknown', 'unsure', 'not_sure'])

function normalizeAnswerValue(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_')
}

export function hasUsableAnswerValue(value: unknown): boolean {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') {
    const normalizedValue = normalizeAnswerValue(value)
    return normalizedValue.length > 0 && !UNCERTAIN_ANSWER_VALUES.has(normalizedValue)
  }
  if (typeof value === 'number') return Number.isFinite(value)
  if (Array.isArray(value)) return value.length > 0 && value.every(hasUsableAnswerValue)
  return true
}

export function filterCurrentCategoryQuestions(
  questions: CategoryQuestionResponse[],
  categoryCode: string,
): CategoryQuestionResponse[] {
  if (categoryCode !== 'EMPLOYMENT') return questions

  return questions.filter(
    (question) =>
      question.question_key !== LEGACY_EMPLOYMENT_COMPANY_SIZE_QUESTION_KEY &&
      !isRepeatedEmploymentStatusQuestion(question),
  )
}

export function isRepeatedEmploymentStatusQuestion(question: CategoryQuestionResponse): boolean {
  if (question.question_key === 'employment.contract_type_code') return false

  return (
    question.question_key.includes('employment_status') ||
    question.label.includes('고용 형태') ||
    question.label.includes('취업 상태') ||
    question.label.includes('취업상태') ||
    question.label.includes('경제활동 상태')
  )
}

export function filterVisibleCategoryQuestions(
  questions: CategoryQuestionResponse[],
  categoryCode: string,
): CategoryQuestionResponse[] {
  return filterCurrentCategoryQuestions(questions, categoryCode).filter(
    (question) => !HIDDEN_QUESTION_KEYS.has(question.question_key),
  )
}
