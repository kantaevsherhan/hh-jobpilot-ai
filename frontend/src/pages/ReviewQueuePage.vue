<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { CheckCheck, Send, SkipForward } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { applyToVacancy, skipVacancy } from '@/api/vacancies'
import AnalysisPanel from '@/components/AnalysisPanel.vue'
import EmptyState from '@/components/EmptyState.vue'
import HHLink from '@/components/HHLink.vue'
import LetterPanel from '@/components/LetterPanel.vue'
import SalaryCell from '@/components/SalaryCell.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useLetters, useVacancies, useVacancy } from '@/queries'
import { useUiStore } from '@/stores/ui'
import type { VacancyFilters } from '@/schemas/vacancy'

const REVIEW_STATUSES = ['REVIEW_REQUIRED', 'RECOMMENDED', 'LETTER_READY', 'APPLY_PREPARED']

const toast = useToast()
const ui = useUiStore()

const filters = computed<VacancyFilters | null>(() =>
  ui.resumeId === null
    ? null
    : { resume_id: ui.resumeId, status: REVIEW_STATUSES, per_page: 50, page: 1 }
)

const { data, isPending, refetch } = useVacancies(filters)

const index = ref(0)
const current = computed(() => data.value?.items[index.value] ?? null)

watch(data, () => {
  if (index.value >= (data.value?.items.length ?? 0)) index.value = 0
})

const { data: detail } = useVacancy(
  () => current.value?.id ?? 0,
  () => (current.value ? ui.resumeId : null)
)
const { data: letters } = useLetters(
  () => current.value?.id ?? 0,
  () => (current.value ? ui.resumeId : null)
)

const selectedLetter = computed(() => letters.value?.find((letter) => letter.is_selected) ?? null)
const busy = ref(false)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 8000 })
}

function next() {
  if (index.value + 1 < (data.value?.items.length ?? 0)) index.value += 1
  else void refetch()
}

async function skipAndNext() {
  if (!current.value || ui.resumeId === null) return
  busy.value = true
  try {
    await skipVacancy(current.value.id, ui.resumeId)
    next()
    await refetch()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}

async function applyAndNext() {
  if (!current.value || ui.resumeId === null) return
  busy.value = true
  try {
    const result = await applyToVacancy(current.value.id, {
      resume_id: ui.resumeId,
      letter_id: selectedLetter.value?.id ?? null,
      runtime_mode: ui.runtimeMode
    })
    toast.add({ severity: 'success', summary: 'Отклик', detail: result.message, life: 6000 })
    next()
    await refetch()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else-if="!current" class="pt-14">
    <EmptyState
      :icon="CheckCheck"
      title="Очередь пуста"
      hint="Здесь появляются вакансии, по которым бот дошёл до решения, но нажать «Откликнуться» должен человек."
    />
  </div>

  <div v-else class="mx-auto max-w-3xl">
    <p class="mb-3 text-[12.5px] text-slate-500">
      {{ index + 1 }} из {{ data?.items.length ?? 0 }} в очереди
    </p>

    <article class="rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="flex items-start gap-3">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-[17px] font-semibold tracking-tight text-slate-900">
              {{ current.title }}
            </h2>
            <HHLink :url="current.url" />
          </div>
          <div class="mt-1 flex flex-wrap items-center gap-x-3 text-[13px] text-slate-600">
            <span>{{ current.company_name ?? 'Компания не указана' }}</span>
            <SalaryCell
              :from="current.salary_from"
              :to="current.salary_to"
              :currency="current.currency"
              :gross="current.salary_gross"
            />
            <StatusTag :code="current.work_format" kind="work_format" />
          </div>
        </div>
        <div class="flex shrink-0 flex-col items-end gap-1">
          <ScoreBadge :score="current.score" />
          <StatusTag :code="current.status" />
        </div>
      </div>

      <div class="mt-4 border-t border-slate-200 pt-4">
        <AnalysisPanel
          :raw="detail?.analysis_json ?? null"
          :hidden-instructions="current.hidden_instructions"
        />
      </div>

      <div class="mt-4 border-t border-slate-200 pt-4">
        <LetterPanel
          v-if="ui.resumeId !== null"
          :vacancy-id="current.id"
          :resume-id="ui.resumeId"
        />
      </div>
    </article>

    <Message v-if="ui.runtimeMode === 'DRY_RUN'" severity="secondary" size="small" class="mt-3">
      Пробный режим: форма откроется и заполнится, но отклик работодателю не отправится.
    </Message>

    <div class="mt-3 flex items-center gap-2">
      <Button
        size="small"
        severity="secondary"
        outlined
        label="Пропустить"
        :loading="busy"
        @click="skipAndNext"
      >
        <template #icon><SkipForward class="mr-1.5 size-3.5" /></template>
      </Button>
      <Button
        class="ml-auto"
        size="small"
        :severity="ui.runtimeMode === 'LIVE' ? 'danger' : 'primary'"
        :label="ui.runtimeMode === 'LIVE' ? 'Откликнуться и далее' : 'Подготовить и далее'"
        :loading="busy"
        :disabled="selectedLetter?.fact_check_passed === false"
        @click="applyAndNext"
      >
        <template #icon><Send class="mr-1.5 size-3.5" /></template>
      </Button>
    </div>
  </div>
</template>
