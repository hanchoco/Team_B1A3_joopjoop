import type { CategoryQuestionResponse } from '../types/api'

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

export function removeDuplicateCompanySizeQuestions(
  questions: CategoryQuestionResponse[],
): CategoryQuestionResponse[] {
  const companySizeQuestions = questions.filter(
    (item) =>
      item.question_key.includes('company_size') ||
      (item.label.includes('회사') && item.label.includes('규모')),
  )
  if (companySizeQuestions.length < 2) return questions

  const detailedQuestion = companySizeQuestions.at(-1)
  return questions.filter(
    (item) => !companySizeQuestions.includes(item) || item.id === detailedQuestion?.id,
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
  return removeDuplicateCompanySizeQuestions(
    questions.filter(
      (question) =>
        !HIDDEN_QUESTION_KEYS.has(question.question_key) &&
        !(categoryCode === 'EMPLOYMENT' && isRepeatedEmploymentStatusQuestion(question)),
    ),
  )
}
