import { z } from 'zod'
import { api } from '@/api/client'

const rangeSchema = z.tuple([z.number(), z.number()])

export const settingsSchema = z.object({
  delays: z.object({
    speed_multiplier: z.number(),
    long_pause_every: z.number(),
    long_pause_range: rangeSchema,
    ranges: z.record(z.string(), rangeSchema)
  }),
  limits: z.object({
    max_applications_per_run: z.number(),
    max_applications_per_day: z.number(),
    max_consecutive_errors: z.number()
  }),
  currency_rates: z.record(z.string(), z.number()),
  tax_rate: z.number(),
  llm: z.object({
    max_vacancy_chars: z.number(),
    letter_min_chars: z.number(),
    letter_max_chars: z.number()
  }),
  bot: z.object({ answer_employer_questions: z.boolean() })
})

export type AppSettings = z.infer<typeof settingsSchema>

export async function fetchSettings(): Promise<AppSettings> {
  const { data } = await api.get<unknown>('/settings')
  return settingsSchema.parse(data)
}

export async function patchSettings(payload: Partial<AppSettings>): Promise<AppSettings> {
  const { data } = await api.patch<unknown>('/settings', payload)
  return settingsSchema.parse(data)
}

export async function createBackup(): Promise<{ path: string; size_bytes: number }> {
  const { data } = await api.post<unknown>('/backup')
  return z.object({ path: z.string(), size_bytes: z.number() }).parse(data)
}

/** Ссылки на выгрузки: проксируются через vite на бэкенд. */
export const exportUrl = (kind: 'vacancies' | 'applications', resumeId: number) =>
  `/api/v1/export/${kind}.csv?resume_id=${String(resumeId)}`
