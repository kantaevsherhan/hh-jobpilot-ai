import { z } from 'zod'

export const skillSchema = z.object({
  id: z.number(),
  name: z.string(),
  is_core: z.boolean()
})

export const resumeSchema = z.object({
  id: z.number(),
  name: z.string(),
  raw_text: z.string(),
  allowed_facts: z.string(),
  hh_resume_url: z.string().nullable(),
  hh_resume_id: z.string().nullable(),
  letter_languages: z.array(z.string()),
  min_score: z.number(),
  auto_apply_score: z.number(),
  digest_json: z.record(z.string(), z.unknown()).nullable(),
  digest_updated_at: z.string().nullable(),
  is_active: z.boolean(),
  is_archived: z.boolean(),
  has_completed_run: z.boolean(),
  skills: z.array(skillSchema),
  created_at: z.string(),
  updated_at: z.string()
})

export type Skill = z.infer<typeof skillSchema>
export type Resume = z.infer<typeof resumeSchema>

export interface ResumeInput {
  name: string
  raw_text?: string
  allowed_facts?: string
  hh_resume_url?: string | null
  letter_languages?: string[]
  min_score?: number
  auto_apply_score?: number
}
