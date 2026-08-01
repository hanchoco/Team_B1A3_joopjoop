import type { NotificationSettingResponse, NotificationSettingUpdatePayload } from '../types/api'
import { apiClient } from './client'

export async function getNotificationSettings(): Promise<NotificationSettingResponse> {
  const response = await apiClient.get<NotificationSettingResponse>(
    '/users/me/notification-settings',
  )
  return response.data
}

export async function updateNotificationSettings(
  payload: NotificationSettingUpdatePayload,
): Promise<NotificationSettingResponse> {
  const response = await apiClient.patch<NotificationSettingResponse>(
    '/users/me/notification-settings',
    payload,
  )
  return response.data
}
