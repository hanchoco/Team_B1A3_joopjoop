import { apiClient } from './client'
import type {
  CategoryAnswerResponse,
  CategoryAnswerUpsert,
  CategoryQuestionResponse,
  CategoryResponse,
} from '../types/api'

export async function listCategories(): Promise<CategoryResponse[]> {
  const response = await apiClient.get<CategoryResponse[]>('/categories')
  return response.data
}

export async function listCategoryQuestions(
  categoryId: number,
): Promise<CategoryQuestionResponse[]> {
  const response = await apiClient.get<CategoryQuestionResponse[]>(
    `/categories/${categoryId}/questions`,
  )
  return response.data
}

export async function saveCategoryAnswers(
  categoryId: number,
  answers: CategoryAnswerUpsert[],
): Promise<CategoryAnswerResponse[]> {
  const response = await apiClient.put<CategoryAnswerResponse[]>(
    `/categories/${categoryId}/answers`,
    { answers },
  )
  return response.data
}
