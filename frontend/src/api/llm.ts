import { z } from 'zod'
import { api } from '@/api/client'
import {
  cliToolSchema,
  promptSchema,
  providerSchema,
  providerTestSchema,
  routingSchema,
  type CliTool,
  type Prompt,
  type Provider,
  type ProviderInput,
  type ProviderTest
} from '@/schemas/llm'

export async function fetchProviders(): Promise<Provider[]> {
  const { data } = await api.get<unknown>('/providers')
  return z.array(providerSchema).parse(data)
}

export async function createProvider(payload: ProviderInput): Promise<Provider> {
  const { data } = await api.post<unknown>('/providers', payload)
  return providerSchema.parse(data)
}

export async function patchProvider(
  id: number,
  payload: Partial<ProviderInput>
): Promise<Provider> {
  const { data } = await api.patch<unknown>(`/providers/${String(id)}`, payload)
  return providerSchema.parse(data)
}

export async function deleteProvider(id: number): Promise<void> {
  await api.delete(`/providers/${String(id)}`)
}

export async function testProvider(id: number): Promise<ProviderTest> {
  const { data } = await api.post<unknown>(`/providers/${String(id)}/test`)
  return providerTestSchema.parse(data)
}

export async function fetchCliCatalog(): Promise<CliTool[]> {
  const { data } = await api.get<unknown>('/providers/cli/catalog')
  return z.array(cliToolSchema).parse(data)
}

export async function fetchRouting(): Promise<Record<string, number>> {
  const { data } = await api.get<unknown>('/providers/routing/current')
  return routingSchema.parse(data).routing
}

export async function saveRouting(
  routing: Record<string, number>
): Promise<Record<string, number>> {
  const { data } = await api.put<unknown>('/providers/routing/current', { routing })
  return routingSchema.parse(data).routing
}

export async function fetchPrompts(): Promise<Prompt[]> {
  const { data } = await api.get<unknown>('/prompts')
  return z.array(promptSchema).parse(data)
}

export async function patchPrompt(key: string, content: string): Promise<Prompt> {
  const { data } = await api.patch<unknown>(`/prompts/${key}`, { content })
  return promptSchema.parse(data)
}

export async function resetPrompt(key: string): Promise<Prompt> {
  const { data } = await api.post<unknown>(`/prompts/${key}/reset`)
  return promptSchema.parse(data)
}
