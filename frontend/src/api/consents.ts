import { apiClient } from './client'
import type { ConsentCreate, ConsentResponse } from '../types/api'

export async function listConsents(): Promise<ConsentResponse[]> {
  const response = await apiClient.get<ConsentResponse[]>('/users/me/consents')
  return response.data
}

export async function updateConsents(consents: ConsentCreate[]): Promise<ConsentResponse[]> {
  const response = await apiClient.put<ConsentResponse[]>('/users/me/consents', { consents })
  return response.data
}
