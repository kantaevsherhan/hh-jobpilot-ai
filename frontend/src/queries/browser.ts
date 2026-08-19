import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  checkBrowserAuth,
  closeBrowser,
  fetchBrowserStatus,
  restartBrowser,
  startBrowser
} from '@/api/browser'

const KEY = ['browser'] as const

export const useBrowserStatus = () =>
  useQuery({ queryKey: KEY, queryFn: fetchBrowserStatus, refetchInterval: 5000 })

function useBrowserAction(fn: () => Promise<unknown>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: KEY })
  })
}

export const useStartBrowser = () => useBrowserAction(startBrowser)
export const useCheckAuth = () => useBrowserAction(checkBrowserAuth)
export const useRestartBrowser = () => useBrowserAction(restartBrowser)
export const useCloseBrowser = () => useBrowserAction(closeBrowser)
