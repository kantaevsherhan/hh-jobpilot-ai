import { z } from 'zod'

export const PROVIDER_TYPES = ['ollama', 'anthropic', 'openai', 'openrouter', 'cli'] as const

export const providerSchema = z.object({
  id: z.number(),
  name: z.string(),
  type: z.string(),
  base_url: z.string().nullable(),
  model: z.string().nullable(),
  temperature: z.number(),
  timeout_sec: z.number(),
  extra_json: z.record(z.string(), z.unknown()),
  is_enabled: z.boolean(),
  api_key_masked: z.string().nullable()
})

export const routingSchema = z.object({ routing: z.record(z.string(), z.number()) })

export const providerTestSchema = z.object({
  ok: z.boolean(),
  response: z.string().optional(),
  elapsed_sec: z.number().optional(),
  error: z.string().optional(),
  details: z.string().nullable().optional()
})

export const promptSchema = z.object({
  id: z.number(),
  key: z.string(),
  title: z.string(),
  content: z.string(),
  updated_at: z.string(),
  is_default: z.boolean()
})

export const cliToolSchema = z.object({
  command: z.string(),
  label: z.string(),
  path: z.string().nullable(),
  efforts: z.array(z.string()),
  models: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      description: z.string(),
      efforts: z.array(z.string()),
      default_effort: z.string().nullable()
    })
  )
})

export type CliTool = z.infer<typeof cliToolSchema>
export type Provider = z.infer<typeof providerSchema>
export type ProviderTest = z.infer<typeof providerTestSchema>
export type Prompt = z.infer<typeof promptSchema>

export interface ProviderInput {
  name: string
  type: string
  base_url?: string | null
  api_key?: string | null
  model?: string | null
  temperature?: number
  timeout_sec?: number
  extra_json?: Record<string, unknown>
  is_enabled?: boolean
}

/** Шаги пайплайна в порядке, в котором они идут по вакансии. */
export const ROUTING_STEPS = [
  { key: 'resume_digest', label: 'Выжимка резюме', hint: 'один раз на резюме' },
  { key: 'analyze', label: 'Анализ вакансии', hint: 'до 25 раз за прогон' },
  { key: 'letter', label: 'Сопроводительное письмо', hint: 'один раз на вакансию' },
  { key: 'fact_check', label: 'Проверка фактов', hint: 'после каждого письма' },
  { key: 'answer_question', label: 'Ответы на вопросы', hint: 'редко' }
] as const
