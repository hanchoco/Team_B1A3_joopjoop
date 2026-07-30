import { apiClient } from './client'
import type {
  EmploymentSimulatorRequest,
  FinanceSimulatorRequest,
  HousingSimulatorRequest,
  SimulatorResult,
  TaxSimulatorRequest,
  TransportSimulatorRequest,
  WelfareSimulatorRequest,
} from '../types/api'

export async function simulateHousing(payload: HousingSimulatorRequest): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>('/simulator/housing', payload)
  return response.data
}

export async function simulateTransport(
  payload: TransportSimulatorRequest,
): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>('/simulator/transport', payload)
  return response.data
}

export async function simulateFinance(payload: FinanceSimulatorRequest): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>('/simulator/finance', payload)
  return response.data
}

export async function simulateTax(payload: TaxSimulatorRequest): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>('/simulator/tax', payload)
  return response.data
}

export async function simulateEmployment(
  payload: EmploymentSimulatorRequest,
): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>('/simulator/employment', payload)
  return response.data
}

export async function simulateWelfare(payload: WelfareSimulatorRequest): Promise<SimulatorResult> {
  const response = await apiClient.post<SimulatorResult>('/simulator/welfare', payload)
  return response.data
}
