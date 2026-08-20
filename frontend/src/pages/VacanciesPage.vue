<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { Inbox, RotateCcw, Search } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { rescanFiltered } from '@/api/vacancies'
import EmptyState from '@/components/EmptyState.vue'
import HHLink from '@/components/HHLink.vue'
import SalaryCell from '@/components/SalaryCell.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useDictionaries, useVacancies } from '@/queries'
import { useUiStore } from '@/stores/ui'
import { formatDate } from '@/utils/format'
import type { VacancyFilters, VacancyRow } from '@/schemas/vacancy'

const router = useRouter()
const toast = useToast()
const ui = useUiStore()
const { data: dictionaries } = useDictionaries()

const search = ref('')
const statuses = ref<string[]>([])
const minScore = ref<number | null>(null)
const minSalary = ref<number | null>(null)
const workFormat = ref<string | null>(null)
const onlySuspicious = ref(false)
const page = ref(1)
const perPage = 25

const statusOptions = computed(() =>
  Object.entries(dictionaries.value?.vacancy_status ?? {}).map(([value, label]) => ({
    value,
    label
  }))
)

const formatOptions = computed(() =>
  Object.entries(dictionaries.value?.work_format ?? {}).map(([value, label]) => ({ value, label }))
)

const filters = computed<VacancyFilters | null>(() => {
  if (ui.resumeId === null) return null
  return {
    resume_id: ui.resumeId,
    search: search.value || undefined,
    status: statuses.value.length ? statuses.value : undefined,
    min_score: minScore.value ?? undefined,
    min_salary: minSalary.value ?? undefined,
    work_format: workFormat.value ?? undefined,
    only_suspicious: onlySuspicious.value || undefined,
    page: page.value,
    per_page: perPage
  }
})

const { data, isPending, refetch } = useVacancies(filters)

// Смена фильтров сбрасывает страницу: иначе на второй странице внезапно пусто
watch([search, statuses, minScore, minSalary, workFormat, onlySuspicious], () => {
  page.value = 1
})

const rescanning = ref(false)

async function rescan() {
  if (ui.resumeId === null) return
  rescanning.value = true
  try {
    const reset = await rescanFiltered(ui.resumeId)
    toast.add({
      severity: 'success',
      summary: 'Отклонённые возвращены',
      detail: `Пересмотрено вакансий: ${String(reset)}. Запустите прогон, чтобы проанализировать заново.`,
      life: 6000
    })
    await refetch()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
  } finally {
    rescanning.value = false
  }
}

function open(row: VacancyRow) {
  void router.push(`/vacancies/${String(row.id)}`)
}
</script>

<template>
  <div v-if="ui.resumeId === null" class="pt-16">
    <EmptyState
      :icon="Inbox"
      title="Не выбрано резюме"
      hint="Вакансии, решения и письма привязаны к резюме. Выберите его в шапке."
    />
  </div>

  <div v-else>
    <div class="mb-3 flex flex-wrap items-end gap-2">
      <div class="relative">
        <Search class="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-slate-400" />
        <InputText
          v-model="search"
          size="small"
          class="w-64 pl-8"
          placeholder="Вакансия или компания"
        />
      </div>
      <MultiSelect
        v-model="statuses"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        placeholder="Статус"
        size="small"
        class="w-52"
        :max-selected-labels="1"
        selected-items-label="статусов: {0}"
      />
      <Select
        v-model="workFormat"
        :options="formatOptions"
        option-label="label"
        option-value="value"
        placeholder="Формат"
        size="small"
        show-clear
        class="w-40"
      />
      <InputNumber
        v-model="minScore"
        placeholder="Оценка от"
        :min="0"
        :max="100"
        size="small"
        class="w-32"
      />
      <InputNumber v-model="minSalary" placeholder="Зарплата от" size="small" class="w-36" />
      <label class="flex items-center gap-2 text-[13px] text-slate-600">
        <ToggleSwitch v-model="onlySuspicious" />
        Подозрительные
      </label>

      <Button
        class="ml-auto"
        size="small"
        severity="secondary"
        outlined
        label="Пересмотреть отклонённые"
        :loading="rescanning"
        @click="rescan"
      >
        <template #icon><RotateCcw class="mr-1.5 size-3.5" /></template>
      </Button>
    </div>

    <DataTable
      :value="data?.items ?? []"
      :loading="isPending"
      data-key="id"
      row-hover
      class="overflow-hidden rounded-[14px] border border-slate-200 bg-white text-[13px]"
      @row-click="open($event.data as VacancyRow)"
    >
      <template #empty>
        <EmptyState
          :icon="Inbox"
          title="Вакансий пока нет"
          hint="Создайте поисковый профиль и запустите прогон — найденное появится здесь."
        />
      </template>

      <Column header="Статус" class="w-40">
        <template #body="{ data: row }: { data: VacancyRow }">
          <StatusTag :code="row.status" />
        </template>
      </Column>

      <Column header="Вакансия">
        <template #body="{ data: row }: { data: VacancyRow }">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-800">{{ row.title }}</span>
            <HHLink :url="row.url" />
          </div>
          <p v-if="row.skip_details" class="mt-0.5 text-[12px] text-slate-500">
            {{ row.skip_details }}
          </p>
        </template>
      </Column>

      <Column header="Компания" class="w-48">
        <template #body="{ data: row }: { data: VacancyRow }">
          <span class="text-slate-600">{{ row.company_name ?? '—' }}</span>
        </template>
      </Column>

      <Column header="Зарплата" class="w-44">
        <template #body="{ data: row }: { data: VacancyRow }">
          <SalaryCell
            :from="row.salary_from"
            :to="row.salary_to"
            :currency="row.currency"
            :gross="row.salary_gross"
          />
        </template>
      </Column>

      <Column header="Формат" class="w-28">
        <template #body="{ data: row }: { data: VacancyRow }">
          <StatusTag :code="row.work_format" kind="work_format" />
        </template>
      </Column>

      <Column header="Оценка" class="w-20">
        <template #body="{ data: row }: { data: VacancyRow }">
          <ScoreBadge :score="row.score" />
        </template>
      </Column>

      <Column header="Найдена" class="w-28">
        <template #body="{ data: row }: { data: VacancyRow }">
          <span class="text-slate-500">{{ formatDate(row.first_seen_at) }}</span>
        </template>
      </Column>

      <Column header="Отклик" class="w-28">
        <template #body="{ data: row }: { data: VacancyRow }">
          <span :class="row.applied_at ? 'text-teal-800' : 'text-slate-400'">
            {{ row.applied_at ? formatDate(row.applied_at) : '—' }}
          </span>
        </template>
      </Column>
    </DataTable>

    <Paginator
      v-if="(data?.total ?? 0) > perPage"
      :rows="perPage"
      :total-records="data?.total ?? 0"
      :first="(page - 1) * perPage"
      class="mt-2 rounded-[12px] border border-slate-200 bg-white"
      @page="page = $event.page + 1"
    />

    <p class="mt-2 text-[12px] text-slate-500">Всего: {{ data?.total ?? 0 }}</p>
  </div>
</template>
