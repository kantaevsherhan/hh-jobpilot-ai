import { z } from 'zod'
import { api } from '@/api/client'

export const botStatusSchema = z.object({
  run_id: z.number().nullable(),
  status: z.string(),
  is_busy: z.boolean(),
  current_job: z.string().nullable(),
  pending_jobs: z.number(),
  counters: z.record(z.string(), z.number()),
  consecutive_errors: z.number()
})

export const runSchema = z.object({
  id: z.number(),
  resume_id: z.number(),
  mode: z.string(),
  runtime_mode: z.string(),
  status: z.string(),
  started_at: z.string(),
  ended_at: z.string().nullable(),
  stop_reason: z.string().nullable(),
  counters_json: z.record(z.string(), z.number()),
  last_error_code: z.string().nullable(),
  last_error_step: z.string().nullable()
})

export const runEventSchema = z.object({
  id: z.number(),
  level: z.string(),
  type: z.string(),
  message: z.string(),
  payload_json: z.record(z.string(), z.unknown()).nullable(),
  created_at: z.string()
})

export type BotStatus = z.infer<typeof botStatusSchema>
export type Run = z.infer<typeof runSchema>
export type RunEvent = z.infer<typeof runEventSchema>

export interface StartPayload {
  resume_id: number
  mode: string
  runtime_mode: string
  search_profile_id?: number | null
}

export async function fetchBotStatus(): Promise<BotStatus> {
  const { data } = await api.get<unknown>('/bot/status')
  return botStatusSchema.parse(data)
}

async function control(path: string, body?: unknown): Promise<BotStatus> {
  const { data } = await api.post<unknown>(`/bot/${path}`, body, { timeout: 120_000 })
  return botStatusSchema.parse(data)
}

export const startBot = (payload: StartPayload) => control('start', payload)
export const pauseBot = () => control('pause')
export const resumeBot = () => control('resume')
export const stopBot = () => control('stop')

export async function fetchRuns(resumeId?: number): Promise<Run[]> {
  const { data } = await api.get<unknown>('/runs', { params: { resume_id: resumeId } })
  return z.array(runSchema).parse(data)
}

export async function fetchRunEvents(runId: number, after: number): Promise<RunEvent[]> {
  const { data } = await api.get<unknown>(`/runs/${String(runId)}/events`, { params: { after } })
  return z.array(runEventSchema).parse(data)
}
