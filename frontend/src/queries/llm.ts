import { type Ref } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  createProvider,
  createSkill,
  deleteProvider,
  deleteSkill,
  fetchCliCatalog,
  fetchPrompts,
  fetchProviders,
  fetchRouting,
  fetchSkills,
  fetchSkillTargets,
  patchPrompt,
  patchProvider,
  patchSkill,
  resetPrompt,
  saveRouting
} from '@/api/llm'
import type { ProviderInput, SkillInput } from '@/schemas/llm'

const PROVIDERS = ['providers'] as const
const PROMPTS = ['prompts'] as const

export const useProviders = () => useQuery({ queryKey: PROVIDERS, queryFn: fetchProviders })
export const useRouting = () =>
  useQuery({ queryKey: [...PROVIDERS, 'routing'], queryFn: fetchRouting })
// staleTime: Infinity — список установленных CLI за время работы формы не меняется
export const useCliCatalog = (enabled: Ref<boolean>) =>
  useQuery({
    queryKey: [...PROVIDERS, 'cli-catalog'],
    queryFn: fetchCliCatalog,
    enabled,
    staleTime: Infinity
  })
export const usePrompts = () => useQuery({ queryKey: PROMPTS, queryFn: fetchPrompts })

function useInvalidating<TArgs, TResult>(
  keys: readonly string[],
  fn: (args: TArgs) => Promise<TResult>
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys })
  })
}

export const useCreateProvider = () => useInvalidating(PROVIDERS, createProvider)
export const useDeleteProvider = () => useInvalidating(PROVIDERS, deleteProvider)
export const useSaveRouting = () => useInvalidating(PROVIDERS, saveRouting)

export const usePatchProvider = () =>
  useInvalidating(PROVIDERS, ({ id, payload }: { id: number; payload: Partial<ProviderInput> }) =>
    patchProvider(id, payload)
  )

export const usePatchPrompt = () =>
  useInvalidating(PROMPTS, ({ key, content }: { key: string; content: string }) =>
    patchPrompt(key, content)
  )

export const useResetPrompt = () => useInvalidating(PROMPTS, resetPrompt)

const SKILLS = ['skills'] as const

export const useSkills = () => useQuery({ queryKey: SKILLS, queryFn: fetchSkills })
export const useSkillTargets = () =>
  useQuery({ queryKey: [...SKILLS, 'targets'], queryFn: fetchSkillTargets, staleTime: Infinity })
export const useCreateSkill = () => useInvalidating(SKILLS, createSkill)
export const useDeleteSkill = () => useInvalidating(SKILLS, deleteSkill)
export const usePatchSkill = () =>
  useInvalidating(SKILLS, ({ id, payload }: { id: number; payload: Partial<SkillInput> }) =>
    patchSkill(id, payload)
  )
