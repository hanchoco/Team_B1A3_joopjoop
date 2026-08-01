import { apiClient } from './client'
import type { SimulateBenefitRequest, SimulatorResult } from '../types/api'

export async function simulatePolicyBenefit(
  policyId: number,
  benefitId: number,
  payload: SimulateBenefitRequest,
): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>(
    `/policies/${policyId}/benefits/${benefitId}/simulate`,
    payload,
  )
  return response.data
}
