import { z } from 'zod'
import { api } from '@/api/client'

export const overviewSchema = z.object({
  found: z.number(),
  suitable: z.number(),
  applied: z.number(),
  rejected: z.number(),
  suspicious: z.number(),
  review: z.number(),
  errors: z.number()
})

export const funnelSchema = z.array(z.object({ stage: z.string(), value: z.number() }))

export const technologiesSchema = z.object({
  top: z.array(z.object({ name: z.string(), count: z.number() })),
  missing_in_resume: z.array(z.object({ name: z.string(), count: z.number() })),
  analyzed_vacancies: z.number()
})

export const salariesSchema = z.object({
  count: z.number(),
  min: z.number().nullable(),
  max: z.number().nullable(),
  avg: z.number().nullable(),
  median: z.number().nullable()
})

export type Overview = z.infer<typeof overviewSchema>
export type Funnel = z.infer<typeof funnelSchema>
export type Technologies = z.infer<typeof technologiesSchema>
export type Salaries = z.infer<typeof salariesSchema>

const get = async (path: string, resumeId: number): Promise<unknown> => {
  const { data } = await api.get<unknown>(`/stats/${path}`, { params: { resume_id: resumeId } })
  return data
}

export const fetchOverview = async (id: number) => overviewSchema.parse(await get('overview', id))
export const fetchFunnel = async (id: number) => funnelSchema.parse(await get('funnel', id))
export const fetchTechnologies = async (id: number) =>
  technologiesSchema.parse(await get('technologies', id))
export const fetchSalaries = async (id: number) => salariesSchema.parse(await get('salaries', id))
