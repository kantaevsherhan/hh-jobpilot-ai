import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

const STORAGE_KEY = 'jobpilot.ui'

export type RuntimeMode = 'DRY_RUN' | 'LIVE'
export type BotMode = 'MANUAL' | 'SEMI_AUTO' | 'AUTO'

interface Persisted {
  resumeId: number | null
  sidebarCollapsed: boolean
  runtimeMode: RuntimeMode
  botMode: BotMode
}

const DEFAULTS: Persisted = {
  resumeId: null,
  sidebarCollapsed: false,
  // Боевой режим включается только руками — это защита от «настроил не то и разослал» (§20)
  runtimeMode: 'DRY_RUN',
  botMode: 'MANUAL'
}

function load(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw !== null) return { ...DEFAULTS, ...(JSON.parse(raw) as Partial<Persisted>) }
  } catch {
    // повреждённый localStorage не должен ронять приложение
  }
  return { ...DEFAULTS }
}

/** Pinia держит только UI-состояние: серверные данные живут в TanStack Query (§27). */
export const useUiStore = defineStore('ui', () => {
  const saved = load()
  const resumeId = ref<number | null>(saved.resumeId)
  const sidebarCollapsed = ref(saved.sidebarCollapsed)
  const runtimeMode = ref<RuntimeMode>(saved.runtimeMode)
  const botMode = ref<BotMode>(saved.botMode)

  watch([resumeId, sidebarCollapsed, runtimeMode, botMode], () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        resumeId: resumeId.value,
        sidebarCollapsed: sidebarCollapsed.value,
        runtimeMode: runtimeMode.value,
        botMode: botMode.value
      })
    )
  })

  const hasResume = computed(() => resumeId.value !== null)
  const isLive = computed(() => runtimeMode.value === 'LIVE')

  return { resumeId, sidebarCollapsed, runtimeMode, botMode, hasResume, isLive }
})
