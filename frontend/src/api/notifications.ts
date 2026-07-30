import apiClient from './client'

export interface NotificationSettingsResponse {
  user_id: number
  notification_enabled: boolean
  deadline_d7_enabled: boolean
  deadline_d3_enabled: boolean
  deadline_d0_enabled: boolean
  email_enabled: boolean
  push_enabled: boolean
  updated_at: string
}

export type NotificationSettingsPatch = Partial<
  Pick<
    NotificationSettingsResponse,
    | 'notification_enabled'
    | 'deadline_d7_enabled'
    | 'deadline_d3_enabled'
    | 'deadline_d0_enabled'
    | 'email_enabled'
    | 'push_enabled'
  >
>

export interface NotificationItem {
  id: number
  policy_id: number | null
  notification_type: string
  title: string
  body: string
  scheduled_at: string
  sent_at: string | null
  read_at: string | null
  send_status: string
}

export async function getNotificationSettings(): Promise<NotificationSettingsResponse> {
  const { data } = await apiClient.get<NotificationSettingsResponse>(
    '/api/v1/users/me/notification-settings',
  )
  return data
}

export async function updateNotificationSettings(
  payload: NotificationSettingsPatch,
): Promise<NotificationSettingsResponse> {
  const { data } = await apiClient.patch<NotificationSettingsResponse>(
    '/api/v1/users/me/notification-settings',
    payload,
  )
  return data
}

export async function getNotifications(): Promise<NotificationItem[]> {
  const { data } = await apiClient.get<NotificationItem[]>('/api/v1/users/me/notifications')
  return data
}

export async function markNotificationRead(notificationId: number): Promise<NotificationItem> {
  const { data } = await apiClient.patch<NotificationItem>(
    `/api/v1/notifications/${notificationId}/read`,
  )
  return data
}
