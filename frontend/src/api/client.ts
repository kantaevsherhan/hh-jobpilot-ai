import axios, { AxiosError } from 'axios'

export interface ApiErrorDetail {
  error_code: string
  human_message: string
  step: string | null
  technical_details: string | null
  recoverable: boolean
  screenshot_path: string | null
}

export const api = axios.create({ baseURL: '/api/v1', timeout: 30_000 })

/** Наружу отдаём одно понятное сообщение: сырой AxiosError в UI не показывается. */
export function toMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as { detail?: ApiErrorDetail | string } | undefined)
      ?.detail
    if (typeof detail === 'string') return detail
    if (detail?.human_message) return detail.human_message
    if (error.code === 'ERR_NETWORK') return 'Бэкенд не отвечает. Запущен ли make dev?'
  }
  return error instanceof Error ? error.message : 'Неизвестная ошибка'
}
