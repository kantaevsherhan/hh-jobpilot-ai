import { z } from 'zod'
import { api } from '@/api/client'
import {
  applicationSchema,
  letterSchema,
  vacancyDetailSchema,
  vacancyPageSchema,
  type Application,
  type Letter,
  type VacancyDetail,
  type VacancyFilters
} from '@/schemas/vacancy'

export async function fetchVacancies(filters: VacancyFilters) {
  const { data } = await api.get<unknown>('/vacancies', { params: filters })
  return vacancyPageSchema.parse(data)
}

export async function fetchVacancy(id: number, resumeId: number): Promise<VacancyDetail> {
  const { data } = await api.get<unknown>(`/vacancies/${String(id)}`, {
    params: { resume_id: resumeId }
  })
  return vacancyDetailSchema.parse(data)
}

export async function skipVacancy(id: number, resumeId: number): Promise<void> {
  await api.post(`/vacancies/${String(id)}/skip`, undefined, { params: { resume_id: resumeId } })
}

export async function unmarkSuspicious(id: number, resumeId: number): Promise<void> {
  await api.post(`/vacancies/${String(id)}/unmark-suspicious`, undefined, {
    params: { resume_id: resumeId }
  })
}

export async function rescanFiltered(resumeId: number): Promise<number> {
  const { data } = await api.post<unknown>('/vacancies/rescan-filtered', undefined, {
    params: { resume_id: resumeId }
  })
  return z.object({ reset: z.number() }).parse(data).reset
}

export async function fetchLetters(vacancyId: number, resumeId: number): Promise<Letter[]> {
  const { data } = await api.get<unknown>(`/vacancies/${String(vacancyId)}/letters`, {
    params: { resume_id: resumeId }
  })
  return z.array(letterSchema).parse(data)
}

export async function writeLetterManually(
  vacancyId: number,
  payload: { resume_id: number; content: string; language?: string }
): Promise<Letter> {
  const { data } = await api.post<unknown>(
    `/vacancies/${String(vacancyId)}/letters/manual`,
    payload
  )
  return letterSchema.parse(data)
}

export async function generateLetter(
  vacancyId: number,
  payload: { resume_id: number; instruction?: string }
): Promise<Letter> {
  // Письмо пишет модель — на локальной это минуты, не секунды
  const { data } = await api.post<unknown>(
    `/vacancies/${String(vacancyId)}/letters/generate`,
    payload,
    { timeout: 600_000 }
  )
  return letterSchema.parse(data)
}

export async function selectLetter(letterId: number): Promise<Letter> {
  const { data } = await api.post<unknown>(`/letters/${String(letterId)}/select`)
  return letterSchema.parse(data)
}

export async function runFactCheck(letterId: number, resumeId: number): Promise<Letter> {
  const { data } = await api.post<unknown>(`/letters/${String(letterId)}/fact-check`, undefined, {
    params: { resume_id: resumeId },
    timeout: 600_000
  })
  return letterSchema.parse(data)
}

export async function applyToVacancy(
  vacancyId: number,
  payload: { resume_id: number; letter_id?: number | null; runtime_mode: string }
) {
  const { data } = await api.post<unknown>(`/vacancies/${String(vacancyId)}/apply`, payload, {
    timeout: 600_000
  })
  return z.object({ status: z.string(), message: z.string() }).parse(data)
}

export async function fetchApplications(resumeId: number): Promise<Application[]> {
  const { data } = await api.get<unknown>('/applications', { params: { resume_id: resumeId } })
  return z.array(applicationSchema).parse(data)
}
