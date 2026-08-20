<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import { FileText, Plus } from 'lucide-vue-next'
import EmptyState from '@/components/EmptyState.vue'
import SetupChecklist from '@/components/SetupChecklist.vue'
import { useBotStatus, useRuns, useStats } from '@/queries'
import { useResumes } from '@/queries/resumes'
import { useUiStore } from '@/stores/ui'
import { formatDateTime, formatDuration } from '@/utils/format'

const ui = useUiStore()
const { data: resumes } = useResumes()
const { data: status } = useBotStatus()
const { data: runs } = useRuns(() => ui.resumeId)
const { overview, funnel, technologies, salaries } = useStats(() => ui.resumeId)

const cards = computed(() => {
  const data = overview.data.value
  if (!data) return []
  return [
    { label: 'Найдено', value: data.found, to: '/vacancies' },
    { label: 'Подходящих', value: data.suitable, to: '/vacancies' },
    { label: 'На проверке', value: data.review, to: '/review' },
    { label: 'Откликов', value: data.applied, to: '/applications' },
    { label: 'Отклонено', value: data.rejected, to: '/vacancies' },
    { label: 'Подозрительных', value: data.suspicious, to: '/suspicious' },
    { label: 'Ошибок', value: data.errors, to: '/activity' }
  ]
})

const activeRun = computed(() => runs.value?.[0] ?? null)

const funnelMax = computed(() =>
  Math.max(1, ...(funnel.data.value ?? []).map((stage) => stage.value))
)

const progress = computed(() => {
  const done = Number(activeRun.value?.counters_json.analyzed ?? 0)
  const pending = status.value?.pending_jobs ?? 0
  return done + pending === 0 ? 0 : Math.round((done / (done + pending)) * 100)
})

const money = (value: number | null) =>
  value === null ? '—' : `${value.toLocaleString('ru-RU')} ₸`
</script>

<template>
  <div v-if="(resumes?.length ?? 0) === 0" class="max-w-3xl">
    <SetupChecklist class="mb-4" />
    <EmptyState
      :icon="FileText"
      title="Начните с резюме"
      hint="Текст резюме — источник истины для всего остального: из него собирается выжимка, по нему пишутся письма и проверяются факты."
    >
      <RouterLink to="/resumes" class="mt-4 inline-block">
        <Button size="small" label="Создать резюме">
          <template #icon><Plus class="mr-1.5 size-4" /></template>
        </Button>
      </RouterLink>
    </EmptyState>
  </div>

  <div v-else-if="ui.resumeId === null" class="pt-14">
    <EmptyState :icon="FileText" title="Выберите резюме" hint="Селектор — в шапке приложения." />
  </div>

  <div v-else class="max-w-5xl">
    <SetupChecklist class="mb-4" />

    <section class="grid grid-cols-4 gap-2.5">
      <RouterLink
        v-for="card in cards"
        :key="card.label"
        :to="card.to"
        class="rounded-[14px] border border-slate-200 bg-white px-4 py-3 no-underline transition-colors hover:border-slate-300"
      >
        <p class="text-[12px] text-slate-500">{{ card.label }}</p>
        <p class="mt-0.5 font-mono text-[22px] tracking-tight tabular-nums text-slate-900">
          {{ card.value }}
        </p>
      </RouterLink>
    </section>

    <section v-if="activeRun" class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="flex flex-wrap items-baseline gap-x-3">
        <h3 class="text-[14px] font-semibold text-slate-800">Прогон №{{ activeRun.id }}</h3>
        <span class="text-[12.5px] text-slate-500">
          {{ formatDateTime(activeRun.started_at) }} ·
          {{ formatDuration(activeRun.started_at, activeRun.ended_at) }}
        </span>
        <span class="ml-auto text-[12.5px] text-slate-600">{{ activeRun.status }}</span>
      </div>
      <template v-if="status?.is_busy">
        <ProgressBar :value="progress" class="mt-3 h-2" :show-value="false" />
        <p class="mt-1.5 text-[12px] text-slate-500">
          Обработано {{ activeRun.counters_json.analyzed ?? 0 }}, осталось
          {{ status.pending_jobs }} задач
        </p>
      </template>
      <RouterLink
        to="/activity"
        class="mt-2 inline-block text-[12.5px] text-teal-700 no-underline hover:underline"
      >
        Смотреть ленту событий
      </RouterLink>
    </section>

    <div class="mt-4 grid grid-cols-[1fr_320px] gap-4">
      <section class="rounded-[14px] border border-slate-200 bg-white p-5">
        <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Воронка</h3>
        <div v-if="(funnel.data.value?.[0]?.value ?? 0) === 0" class="text-[13px] text-slate-500">
          Данных пока нет — воронка появится после первого прогона.
        </div>
        <div v-else class="space-y-2">
          <div v-for="stage in funnel.data.value ?? []" :key="stage.stage">
            <div class="mb-1 flex items-baseline justify-between">
              <span class="text-[12.5px] text-slate-600">{{ stage.stage }}</span>
              <span class="font-mono text-[12.5px] tabular-nums text-slate-800">
                {{ stage.value }}
              </span>
            </div>
            <div class="h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                class="h-full rounded-full bg-teal-700/70"
                :style="{ width: `${String(Math.round((stage.value / funnelMax) * 100))}%` }"
              />
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-[14px] border border-slate-200 bg-white p-5">
        <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Зарплаты</h3>
        <div v-if="(salaries.data.value?.count ?? 0) === 0" class="text-[13px] text-slate-500">
          Нет данных по подходящим вакансиям.
        </div>
        <dl v-else class="space-y-1.5 text-[13px]">
          <div class="flex justify-between">
            <dt class="text-slate-500">Медиана</dt>
            <dd class="font-mono tabular-nums text-slate-900">
              {{ money(salaries.data.value?.median ?? null) }}
            </dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Среднее</dt>
            <dd class="font-mono tabular-nums text-slate-700">
              {{ money(salaries.data.value?.avg ?? null) }}
            </dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Минимум</dt>
            <dd class="font-mono tabular-nums text-slate-700">
              {{ money(salaries.data.value?.min ?? null) }}
            </dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Максимум</dt>
            <dd class="font-mono tabular-nums text-slate-700">
              {{ money(salaries.data.value?.max ?? null) }}
            </dd>
          </div>
          <p class="pt-1 text-[12px] text-slate-400">
            по {{ salaries.data.value?.count ?? 0 }} вакансиям в тенге
          </p>
        </dl>
      </section>
    </div>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="mb-3 flex items-baseline gap-3">
        <h3 class="text-[13.5px] font-semibold text-slate-800">Требования рынка</h3>
        <span class="text-[12px] text-slate-500">
          по {{ technologies.data.value?.analyzed_vacancies ?? 0 }} проанализированным вакансиям
        </span>
      </div>

      <div
        v-if="(technologies.data.value?.top.length ?? 0) === 0"
        class="text-[13px] text-slate-500"
      >
        Появится после того, как модель проанализирует первые вакансии.
      </div>

      <div v-else class="grid grid-cols-2 gap-6">
        <div>
          <p class="mb-2 text-[12px] font-medium text-slate-500">Чаще всего требуют</p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="item in technologies.data.value?.top.slice(0, 18) ?? []"
              :key="item.name"
              class="rounded-full bg-slate-100 px-2.5 py-0.5 text-[12.5px] text-slate-700"
            >
              {{ item.name }}
              <span class="text-slate-400">{{ item.count }}</span>
            </span>
          </div>
        </div>
        <div>
          <p class="mb-2 text-[12px] font-medium text-slate-500">Требуют, а в резюме этого нет</p>
          <div
            v-if="(technologies.data.value?.missing_in_resume.length ?? 0) === 0"
            class="text-[13px] text-slate-500"
          >
            Пробелов не нашлось.
          </div>
          <div v-else class="flex flex-wrap gap-1.5">
            <span
              v-for="item in technologies.data.value?.missing_in_resume.slice(0, 18) ?? []"
              :key="item.name"
              class="rounded-full bg-amber-100 px-2.5 py-0.5 text-[12.5px] text-amber-900"
            >
              {{ item.name }}
              <span class="text-amber-700/70">{{ item.count }}</span>
            </span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
