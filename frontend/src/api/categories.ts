import apiClient from './client'

export type CategoryCode =
  | 'HOUSING'
  | 'TRANSPORT'
  | 'FINANCE'
  | 'TAX'
  | 'EMPLOYMENT'
  | 'WELFARE'
  | 'PARTICIPATION'
  | 'ETC'

export type AnswerType =
  | 'SINGLE_SELECT'
  | 'MULTI_SELECT'
  | 'NUMBER'
  | 'BOOLEAN'
  | 'TEXT'
  | 'DATE'

export interface Category {
  id: number
  code: CategoryCode
  name: string
  description: string | null
  display_order: number
  is_active: boolean
}

export interface CategoryQuestion {
  id: number
  category_id: number
  question_key: string
  label: string
  description: string | null
  answer_type: AnswerType
  options_json: unknown
  unit: string | null
  is_required: boolean
  is_used_for_matching: boolean
  display_order: number
  is_active: boolean
}

export async function getCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>('/api/v1/categories')
  return data
}

export async function getCategoryQuestions(categoryId: number): Promise<CategoryQuestion[]> {
  const { data } = await apiClient.get<CategoryQuestion[]>(
    `/api/v1/categories/${categoryId}/questions`,
  )
  return data
}

export async function saveCategoryAnswers(
  categoryId: number,
  answers: Array<{ question_id: number; answer_json: { value: string | number | boolean | string[] } }>,
): Promise<void> {
  await apiClient.put(`/api/v1/categories/${categoryId}/answers`, { answers })
}
