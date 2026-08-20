import { z } from 'zod'

export const vacancyRowSchema = z.object({
  id: z.number(),
  hh_id: z.string(),
  url: z.string(),
  title: z.string(),
  company_name: z.string().nullable(),
  salary_from: z.number().nullable(),
  salary_to: z.number().nullable(),
  currency: z.string().nullable(),
  salary_gross: z.boolean().nullable(),
  work_format: z.string().nullable(),
  experience: z.string().nullable(),
  area: z.string().nullable(),
  published_at: z.string().nullable(),
  first_seen_at: z.string(),
  is_closed: z.boolean(),
  status: z.string().nullable(),
  skip_reason: z.string().nullable(),
  skip_details: z.string().nullable(),
  score: z.number().nullable(),
  is_suspicious: z.boolean(),
  hidden_instructions: z.array(z.unknown()),
  decision_id: z.number().nullable(),
  applied_at: z.string().nullable()
})

export const vacancyDetailSchema = vacancyRowSchema.extend({
  description: z.string(),
  description_lang: z.string().nullable(),
  analysis_json: z.record(z.string(), z.unknown()).nullable(),
  suspicious_reasons: z.array(z.unknown())
})

export const vacancyPageSchema = z.object({
  items: z.array(vacancyRowSchema),
  total: z.number()
})

export const letterSchema = z.object({
  id: z.number(),
  version: z.number(),
  source: z.string(),
  language: z.string(),
  content: z.string(),
  char_count: z.number(),
  fact_check_json: z.record(z.string(), z.unknown()).nullable(),
  fact_check_passed: z.boolean().nullable(),
  is_selected: z.boolean(),
  created_at: z.string()
})

export const applicationSchema = z.object({
  id: z.number(),
  vacancy_id: z.number(),
  resume_id: z.number(),
  letter_id: z.number().nullable(),
  applied_at: z.string(),
  hh_status: z.string().nullable(),
  hh_status_checked_at: z.string().nullable(),
  error_code: z.string().nullable(),
  vacancy_title: z.string(),
  vacancy_url: z.string(),
  company_name: z.string().nullable()
})

/** Разбор ответа модели: показываем только то, что реально пришло. */
export const analysisSchema = z.object({
  score: z.number().optional(),
  score_breakdown: z.record(z.string(), z.number()).optional(),
  required_skills: z.array(z.string()).optional(),
  preferred_skills: z.array(z.string()).optional(),
  matched_skills: z.array(z.string()).optional(),
  missing_skills: z.array(z.string()).optional(),
  critical_missing: z.array(z.string()).optional(),
  red_flags: z.array(z.string()).optional(),
  green_flags: z.array(z.string()).optional(),
  reason: z.string().optional(),
  profession_match: z.boolean().optional(),
  can_do_job: z.boolean().optional()
})

export type VacancyRow = z.infer<typeof vacancyRowSchema>
export type VacancyDetail = z.infer<typeof vacancyDetailSchema>
export type Letter = z.infer<typeof letterSchema>
export type Application = z.infer<typeof applicationSchema>
export type Analysis = z.infer<typeof analysisSchema>

export interface VacancyFilters {
  resume_id: number
  search?: string
  status?: string[]
  min_score?: number
  min_salary?: number
  work_format?: string
  company?: string
  only_suspicious?: boolean
  page?: number
  per_page?: number
}
