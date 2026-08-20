import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  fetchBotStatus,
  fetchRunEvents,
  fetchRuns,
  pauseBot,
  resumeBot,
  startBot,
  stopBot
} from '@/api/bot'
import { fetchDictionaries } from '@/api/catalogs'
import * as catalogs from '@/api/catalogs'
import * as stats from '@/api/stats'
import * as vacancies from '@/api/vacancies'
import { createBackup, fetchSettings, patchSettings, type AppSettings } from '@/api/settings'
import type { VacancyFilters } from '@/schemas/vacancy'

/** Пока бот работает, состояние опрашивается; когда стоит — опрос прекращается (§27). */
export function useBotStatus() {
  return useQuery({
    queryKey: ['bot'],
    queryFn: fetchBotStatus,
    refetchInterval: (query) => (query.state.data?.is_busy === true ? 2000 : false)
  })
}

export function useBotControls() {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries()
  return {
    start: useMutation({ mutationFn: startBot, onSettled: invalidate }),
    pause: useMutation({ mutationFn: pauseBot, onSettled: invalidate }),
    resume: useMutation({ mutationFn: resumeBot, onSettled: invalidate }),
    stop: useMutation({ mutationFn: stopBot, onSettled: invalidate })
  }
}

export const useRuns = (resumeId: MaybeRefOrGetter<number | null>) =>
  useQuery({
    queryKey: ['runs', resumeId],
    queryFn: () => fetchRuns(toValue(resumeId) ?? undefined),
    enabled: () => toValue(resumeId) !== null
  })

export const useDictionaries = () =>
  useQuery({ queryKey: ['dictionaries'], queryFn: fetchDictionaries, staleTime: Infinity })

export function useVacancies(filters: MaybeRefOrGetter<VacancyFilters | null>) {
  return useQuery({
    queryKey: ['vacancies', filters],
    queryFn: () => {
      const value = toValue(filters)
      if (!value) throw new Error('Не выбрано резюме')
      return vacancies.fetchVacancies(value)
    },
    enabled: () => toValue(filters) !== null
  })
}

export function useVacancy(
  id: MaybeRefOrGetter<number>,
  resumeId: MaybeRefOrGetter<number | null>
) {
  return useQuery({
    queryKey: ['vacancy', id, resumeId],
    queryFn: () => vacancies.fetchVacancy(toValue(id), toValue(resumeId) ?? 0),
    enabled: () => toValue(resumeId) !== null
  })
}

export function useLetters(
  vacancyId: MaybeRefOrGetter<number>,
  resumeId: MaybeRefOrGetter<number | null>
) {
  return useQuery({
    queryKey: ['letters', vacancyId, resumeId],
    queryFn: () => vacancies.fetchLetters(toValue(vacancyId), toValue(resumeId) ?? 0),
    enabled: () => toValue(resumeId) !== null
  })
}

export const useApplications = (resumeId: MaybeRefOrGetter<number | null>) =>
  useQuery({
    queryKey: ['applications', resumeId],
    queryFn: () => vacancies.fetchApplications(toValue(resumeId) ?? 0),
    enabled: () => toValue(resumeId) !== null
  })

export const useSearchProfiles = (resumeId: MaybeRefOrGetter<number | null>) =>
  useQuery({
    queryKey: ['search-profiles', resumeId],
    queryFn: () => catalogs.fetchSearchProfiles(toValue(resumeId) ?? 0),
    enabled: () => toValue(resumeId) !== null
  })

export const useCompanyRules = (resumeId: MaybeRefOrGetter<number | null>) =>
  useQuery({
    queryKey: ['company-rules', resumeId],
    queryFn: () => catalogs.fetchCompanyRules(toValue(resumeId) ?? undefined)
  })

export const useLetterExamples = (resumeId: MaybeRefOrGetter<number | null>) =>
  useQuery({
    queryKey: ['letter-examples', resumeId],
    queryFn: () => catalogs.fetchLetterExamples(toValue(resumeId) ?? 0),
    enabled: () => toValue(resumeId) !== null
  })

export const useSettings = () => useQuery({ queryKey: ['settings'], queryFn: fetchSettings })

export function useMutate<TArgs, TResult>(keys: string[], fn: (args: TArgs) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      for (const key of keys) void queryClient.invalidateQueries({ queryKey: [key] })
    }
  })
}

export const usePatchSettings = () =>
  useMutate(['settings'], (payload: Partial<AppSettings>) => patchSettings(payload))
export const useBackup = () => useMutate([], createBackup)

export function useStats(resumeId: MaybeRefOrGetter<number | null>) {
  const enabled = () => toValue(resumeId) !== null
  const id = computed(() => toValue(resumeId) ?? 0)
  return {
    overview: useQuery({
      queryKey: ['stats', 'overview', resumeId],
      queryFn: () => stats.fetchOverview(id.value),
      enabled
    }),
    funnel: useQuery({
      queryKey: ['stats', 'funnel', resumeId],
      queryFn: () => stats.fetchFunnel(id.value),
      enabled
    }),
    technologies: useQuery({
      queryKey: ['stats', 'technologies', resumeId],
      queryFn: () => stats.fetchTechnologies(id.value),
      enabled
    }),
    salaries: useQuery({
      queryKey: ['stats', 'salaries', resumeId],
      queryFn: () => stats.fetchSalaries(id.value),
      enabled
    })
  }
}

export { fetchRunEvents }
