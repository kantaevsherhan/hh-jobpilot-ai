import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'jobpilot.ui'

interface Persisted {
  resumeId: number | null
  sidebarCollapsed: boolean
}

function load(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw !== null) return JSON.parse(raw) as Persisted
  } catch {
    // повреждённый localStorage не должен ронять приложение
  }
  return { resumeId: null, sidebarCollapsed: false }
}

/** Pinia держит только UI-состояние: серверные данные живут в TanStack Query (§27). */
export const useUiStore = defineStore('ui', () => {
  const saved = load()
  const resumeId = ref<number | null>(saved.resumeId)
  const sidebarCollapsed = ref(saved.sidebarCollapsed)

  watch([resumeId, sidebarCollapsed], () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ resumeId: resumeId.value, sidebarCollapsed: sidebarCollapsed.value })
    )
  })

  const hasResume = computed(() => resumeId.value !== null)

  return { resumeId, sidebarCollapsed, hasResume }
})
