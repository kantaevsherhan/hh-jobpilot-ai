import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import {
  archiveResume,
  createResume,
  deleteResume,
  duplicateResume,
  fetchResume,
  fetchResumes,
  patchResume,
  rebuildDigest,
  saveSkills
} from '@/api/resumes'
import type { ResumeInput, Skill } from '@/schemas/resume'

const KEY = ['resumes'] as const

export function useResumes(includeArchived: MaybeRefOrGetter<boolean> = false) {
  return useQuery({
    queryKey: [...KEY, includeArchived],
    queryFn: () => fetchResumes(toValue(includeArchived))
  })
}

export function useResume(id: MaybeRefOrGetter<number | null>) {
  return useQuery({
    queryKey: [...KEY, 'one', id],
    queryFn: () => fetchResume(toValue(id) ?? 0),
    enabled: () => toValue(id) !== null
  })
}

/** Все мутации резюме сбрасывают один и тот же кеш — держим это в одном месте. */
function useResumeMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY })
  })
}

export const useCreateResume = () => useResumeMutation(createResume)
export const useDuplicateResume = () => useResumeMutation(duplicateResume)
export const useArchiveResume = () => useResumeMutation(archiveResume)
export const useDeleteResume = () => useResumeMutation(deleteResume)

export const usePatchResume = () =>
  useResumeMutation(({ id, payload }: { id: number; payload: Partial<ResumeInput> }) =>
    patchResume(id, payload)
  )

export const useSaveSkills = () =>
  useResumeMutation(({ id, skills }: { id: number; skills: Skill[] }) => saveSkills(id, skills))

export const useRebuildDigest = () => useResumeMutation(rebuildDigest)
