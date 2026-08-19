import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  createProvider,
  deleteProvider,
  fetchPrompts,
  fetchProviders,
  fetchRouting,
  patchPrompt,
  patchProvider,
  resetPrompt,
  saveRouting
} from '@/api/llm'
import type { ProviderInput } from '@/schemas/llm'

const PROVIDERS = ['providers'] as const
const PROMPTS = ['prompts'] as const

export const useProviders = () => useQuery({ queryKey: PROVIDERS, queryFn: fetchProviders })
export const useRouting = () =>
  useQuery({ queryKey: [...PROVIDERS, 'routing'], queryFn: fetchRouting })
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
