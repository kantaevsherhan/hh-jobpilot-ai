import { api } from '@/api/client'
import {
  resumeSchema,
  skillSchema,
  type Resume,
  type ResumeInput,
  type Skill
} from '@/schemas/resume'
import { z } from 'zod'

export async function fetchResumes(includeArchived = false): Promise<Resume[]> {
  const { data } = await api.get<unknown>('/resumes', {
    params: { include_archived: includeArchived }
  })
  return z.array(resumeSchema).parse(data)
}

export async function fetchResume(id: number): Promise<Resume> {
  const { data } = await api.get<unknown>(`/resumes/${String(id)}`)
  return resumeSchema.parse(data)
}

export async function createResume(payload: ResumeInput): Promise<Resume> {
  const { data } = await api.post<unknown>('/resumes', payload)
  return resumeSchema.parse(data)
}

export async function patchResume(id: number, payload: Partial<ResumeInput>): Promise<Resume> {
  const { data } = await api.patch<unknown>(`/resumes/${String(id)}`, payload)
  return resumeSchema.parse(data)
}

export async function duplicateResume(id: number): Promise<Resume> {
  const { data } = await api.post<unknown>(`/resumes/${String(id)}/duplicate`)
  return resumeSchema.parse(data)
}

export async function archiveResume(id: number): Promise<Resume> {
  const { data } = await api.post<unknown>(`/resumes/${String(id)}/archive`)
  return resumeSchema.parse(data)
}

export async function deleteResume(id: number): Promise<void> {
  await api.delete(`/resumes/${String(id)}`)
}

export async function saveSkills(id: number, skills: Skill[]): Promise<Skill[]> {
  const { data } = await api.put<unknown>(`/resumes/${String(id)}/skills`, { skills })
  return z.array(skillSchema).parse(data)
}
