import apiClient from './client'

export type SimulatorCategory =
  'housing' | 'transport' | 'finance' | 'tax' | 'employment' | 'welfare'

export type SimulatorPayload = Record<string, number>

export interface SimulatorResult {
  category: Uppercase<SimulatorCategory>
  monthly_before_amount: string | number
  monthly_after_amount: string | number
  monthly_savings_amount: string | number
  annual_before_amount: string | number
  annual_after_amount: string | number
  annual_savings_amount: string | number
  total_benefit_amount: string | number
  support_months: number
  breakdown: Record<string, string | number>
  disclaimer: string
}

export async function runSimulation(
  category: SimulatorCategory,
  payload: SimulatorPayload,
): Promise<SimulatorResult> {
  const { data } = await apiClient.post<SimulatorResult>(`/api/v1/simulator/${category}`, payload)
  return data
}
