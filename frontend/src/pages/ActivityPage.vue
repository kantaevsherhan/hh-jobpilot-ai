<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import ProgressBar from 'primevue/progressbar'
import { Activity, AlertTriangle, Info, TriangleAlert } from 'lucide-vue-next'
import { fetchRunEvents, useBotStatus, useRuns } from '@/queries'
import type { RunEvent } from '@/api/bot'
import EmptyState from '@/components/EmptyState.vue'
import { useUiStore } from '@/stores/ui'
import {
  formatBotMode,
  formatDateTime,
  formatDuration,
  formatRuntimeMode,
  formatTime
} from '@/utils/format'

const ui = useUiStore()
const { data: status } = useBotStatus()
const { data: runs } = useRuns(() => ui.resumeId)

const events = ref<RunEvent[]>([])
const lastId = ref(0)
let timer: number | undefined

const activeRun = computed(() => runs.value?.[0] ?? null)
const runId = computed(() => status.value?.run_id ?? activeRun.value?.id ?? null)

const counters = computed(() => activeRun.value?.counters_json ?? {})

const progress = computed(() => {
  const done = Number(counters.value.analyzed ?? 0)
  const pending = status.value?.pending_jobs ?? 0
  const total = done + pending
  return total === 0 ? 0 : Math.round((done / total) * 100)
})

const COUNTER_LABELS: Record<string, string> = {
  found: 'Найдено',
  new: 'Новых',
  filtered: 'Отсеяно фильтрами',
  analyzed: 'Проанализировано',
  suitable: 'Подходящих',
  review: 'На проверке',
  applied: 'Откликов',
  suspicious: 'Подозрительных',
  errors: 'Ошибок'
}

async function poll() {
  if (runId.value === null) return
  const fresh = await fetchRunEvents(runId.value, lastId.value)
  if (fresh.length) {
    events.value = [...events.value, ...fresh].slice(-500)
    lastId.value = fresh[fresh.length - 1].id
  }
}

// Лента дописывается в конец, а не перезагружается целиком (§27)
watch(
  runId,
  (value) => {
    events.value = []
    lastId.value = 0
    if (value !== null) void poll()
  },
  { immediate: true }
)

watch(
  () => status.value?.is_busy ?? false,
  (busy) => {
    window.clearInterval(timer)
    if (busy) timer = window.setInterval(() => void poll(), 2000)
    else void poll()
  },
  { immediate: true }
)

onUnmounted(() => {
  window.clearInterval(timer)
})

const ICONS: Record<string, typeof Info> = {
  info: Info,
  warning: TriangleAlert,
  error: AlertTriangle,
  debug: Info
}

const TONES: Record<string, string> = {
  info: 'text-slate-600',
  warning: 'text-amber-700',
  error: 'text-red-700',
  debug: 'text-slate-400'
}
</script>

<template>
  <div class="mx-auto w-full max-w-7xl">
    <section v-if="activeRun" class="mb-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 class="text-[15px] font-semibold tracking-tight text-slate-900">
          Прогон №{{ activeRun.id }}
        </h2>
        <span class="text-[12.5px] text-slate-500">
          {{ formatDateTime(activeRun.started_at) }} ·
          {{ formatDuration(activeRun.started_at, activeRun.ended_at) }}
        </span>
        <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11.5px] text-slate-700">
          {{ formatBotMode(activeRun.mode) }} · {{ formatRuntimeMode(activeRun.runtime_mode) }}
        </span>
        <span class="ml-auto text-[12.5px] text-slate-600">{{ activeRun.status }}</span>
      </div>

      <ProgressBar v-if="status?.is_busy" :value="progress" class="mt-3 h-2" :show-value="false" />
      <p v-if="status?.is_busy" class="mt-1.5 text-[12px] text-slate-500">
        Осталось задач: {{ status.pending_jobs }} · сейчас: {{ status.current_job ?? '—' }}
      </p>

      <div class="mt-4 flex flex-wrap gap-x-6 gap-y-2">
        <div v-for="(label, key) in COUNTER_LABELS" :key="key">
          <span class="text-[12px] text-slate-500">{{ label }}</span>
          <span class="ml-1.5 text-[13px] tabular-nums text-slate-800">
            {{ counters[key] ?? 0 }}
          </span>
        </div>
      </div>

      <div
        v-if="activeRun.stop_reason && activeRun.stop_reason !== 'FINISHED'"
        class="mt-4 rounded-[10px] bg-red-50 px-4 py-3"
      >
        <p class="text-[13px] font-medium text-red-900">
          Прогон остановлен: {{ activeRun.stop_reason }}
        </p>
        <p v-if="activeRun.last_error_step" class="mt-0.5 text-[12.5px] text-red-800">
          Шаг: {{ activeRun.last_error_step }} · код: {{ activeRun.last_error_code }}
        </p>
      </div>
    </section>

    <section class="overflow-hidden rounded-[14px] border border-slate-200 bg-white">
      <div v-if="events.length === 0">
        <EmptyState
          :icon="Activity"
          title="Событий пока нет"
          hint="Здесь появляется всё, что делает бот: поиск, анализ, письма, отклики и ошибки."
        />
      </div>

      <ul v-else class="divide-y divide-slate-100">
        <li
          v-for="event in [...events].reverse()"
          :key="event.id"
          class="flex items-start gap-2.5 px-4 py-2"
        >
          <component
            :is="ICONS[event.level] ?? Info"
            class="mt-0.5 size-3.5 shrink-0"
            :class="TONES[event.level] ?? 'text-slate-500'"
          />
          <span class="shrink-0 text-[11.5px] text-slate-400">
            {{ formatTime(event.created_at) }}
          </span>
          <span class="min-w-0 flex-1 text-[13px]" :class="TONES[event.level] ?? 'text-slate-700'">
            {{ event.message }}
          </span>
        </li>
      </ul>
    </section>
  </div>
</template>
