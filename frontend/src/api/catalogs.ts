import { z } from 'zod'
import { api } from '@/api/client'

export const dictionariesSchema = z.record(z.string(), z.record(z.string(), z.string()))

export const searchProfileSchema = z.object({
  id: z.number(),
  resume_id: z.number(),
  name: z.string(),
  enabled: z.boolean(),
  priority: z.number(),
  remote_mode: z.string(),
  min_salary: z.number().nullable(),
  currency: z.string(),
  allow_unknown_salary: z.boolean(),
  experience_levels: z.array(z.unknown()),
  areas: z.array(z.unknown()),
  max_age_days: z.number().nullable(),
  include_keywords: z.array(z.unknown()),
  exclude_keywords: z.array(z.unknown()),
  max_vacancies_per_run: z.number(),
  queries: z.array(z.object({ id: z.number(), text: z.string() }))
})

export const companyRuleSchema = z.object({
  id: z.number(),
  resume_id: z.number().nullable(),
  match_type: z.string(),
  value: z.string(),
  case_sensitive: z.boolean(),
  action: z.string(),
  score_delta: z.number(),
  note: z.string().nullable(),
  enabled: z.boolean()
})

export const letterExampleSchema = z.object({
  id: z.number(),
  resume_id: z.number().nullable(),
  name: z.string(),
  category: z.string(),
  tone: z.string(),
  content: z.string(),
  is_active: z.boolean(),
  is_preferred: z.boolean()
})

export type Dictionaries = z.infer<typeof dictionariesSchema>
export type SearchProfile = z.infer<typeof searchProfileSchema>
export type CompanyRule = z.infer<typeof companyRuleSchema>
export type LetterExample = z.infer<typeof letterExampleSchema>

export async function fetchDictionaries(): Promise<Dictionaries> {
  const { data } = await api.get<unknown>('/dictionaries')
  return dictionariesSchema.parse(data)
}

export async function fetchSearchProfiles(resumeId: number): Promise<SearchProfile[]> {
  const { data } = await api.get<unknown>('/search-profiles', { params: { resume_id: resumeId } })
  return z.array(searchProfileSchema).parse(data)
}

export async function createSearchProfile(
  payload: Record<string, unknown>
): Promise<SearchProfile> {
  const { data } = await api.post<unknown>('/search-profiles', payload)
  return searchProfileSchema.parse(data)
}

export async function patchSearchProfile(
  id: number,
  payload: Record<string, unknown>
): Promise<SearchProfile> {
  const { data } = await api.patch<unknown>(`/search-profiles/${String(id)}`, payload)
  return searchProfileSchema.parse(data)
}

export async function deleteSearchProfile(id: number): Promise<void> {
  await api.delete(`/search-profiles/${String(id)}`)
}

export async function fetchCompanyRules(resumeId?: number): Promise<CompanyRule[]> {
  const { data } = await api.get<unknown>('/company-rules', { params: { resume_id: resumeId } })
  return z.array(companyRuleSchema).parse(data)
}

export async function createCompanyRule(payload: Record<string, unknown>): Promise<CompanyRule> {
  const { data } = await api.post<unknown>('/company-rules', payload)
  return companyRuleSchema.parse(data)
}

export async function deleteCompanyRule(id: number): Promise<void> {
  await api.delete(`/company-rules/${String(id)}`)
}

export async function testCompanyRules(companyName: string, resumeId?: number) {
  const { data } = await api.post<unknown>('/company-rules/test', {
    company_name: companyName,
    resume_id: resumeId
  })
  return z
    .object({
      company_name: z.string(),
      matched: z.array(
        z.object({
          id: z.number(),
          value: z.string(),
          action: z.string(),
          score_delta: z.number()
        })
      )
    })
    .parse(data)
}

export async function fetchLetterExamples(resumeId: number): Promise<LetterExample[]> {
  const { data } = await api.get<unknown>('/letter-examples', { params: { resume_id: resumeId } })
  return z.array(letterExampleSchema).parse(data)
}

export async function createLetterExample(
  payload: Record<string, unknown>
): Promise<LetterExample> {
  const { data } = await api.post<unknown>('/letter-examples', payload)
  return letterExampleSchema.parse(data)
}

export async function patchLetterExample(
  id: number,
  payload: Record<string, unknown>
): Promise<LetterExample> {
  const { data } = await api.patch<unknown>(`/letter-examples/${String(id)}`, payload)
  return letterExampleSchema.parse(data)
}

export async function deleteLetterExample(id: number): Promise<void> {
  await api.delete(`/letter-examples/${String(id)}`)
}
