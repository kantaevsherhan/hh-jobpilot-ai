import { z } from 'zod'
import { api } from '@/api/client'

export const browserStatusSchema = z.object({
  state: z.string(),
  label: z.string(),
  is_running: z.boolean(),
  user_data_dir: z.string(),
  last_error: z.string().nullable()
})

export type BrowserStatus = z.infer<typeof browserStatusSchema>

async function post(path: string): Promise<BrowserStatus> {
  // Запуск браузера с профилем занимает несколько секунд
  const { data } = await api.post<unknown>(`/browser/${path}`, undefined, { timeout: 120_000 })
  return browserStatusSchema.parse(data)
}

export async function fetchBrowserStatus(): Promise<BrowserStatus> {
  const { data } = await api.get<unknown>('/browser/status')
  return browserStatusSchema.parse(data)
}

export const startBrowser = () => post('start')
export const checkBrowserAuth = () => post('check-auth')
export const restartBrowser = () => post('restart')
export const closeBrowser = () => post('close')
