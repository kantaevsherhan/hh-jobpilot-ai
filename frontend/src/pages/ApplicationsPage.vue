<script setup lang="ts">
import { computed } from 'vue'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import { Send } from 'lucide-vue-next'
import EmptyState from '@/components/EmptyState.vue'
import HHLink from '@/components/HHLink.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useApplications } from '@/queries'
import { useUiStore } from '@/stores/ui'
import { formatDateTime } from '@/utils/format'
import type { Application } from '@/schemas/vacancy'

const ui = useUiStore()
const { data: applications, isPending } = useApplications(() => ui.resumeId)

const total = computed(() => applications.value?.length ?? 0)
</script>

<template>
  <div class="mx-auto w-full max-w-7xl">
    <p class="mb-3 text-[13px] text-slate-600">
      Отправлено откликов: <span class="font-medium text-slate-800">{{ total }}</span>
    </p>

    <DataTable
      :value="applications ?? []"
      :loading="isPending"
      data-key="id"
      class="overflow-hidden rounded-[14px] border border-slate-200 bg-white text-[13px]"
    >
      <template #empty>
        <EmptyState
          :icon="Send"
          title="Откликов ещё не было"
          hint="История откликов хранится в базе и переживает перезапуск приложения."
        />
      </template>

      <Column header="Дата" class="w-40">
        <template #body="{ data }: { data: Application }">
          <span class="text-slate-600">{{ formatDateTime(data.applied_at) }}</span>
        </template>
      </Column>

      <Column header="Вакансия">
        <template #body="{ data }: { data: Application }">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-800">{{ data.vacancy_title }}</span>
            <HHLink :url="data.vacancy_url" />
          </div>
          <p class="text-[12px] text-slate-500">{{ data.company_name ?? '—' }}</p>
        </template>
      </Column>

      <Column header="Статус на HH" class="w-44">
        <template #body="{ data }: { data: Application }">
          <StatusTag :code="data.hh_status" kind="hh_application_status" />
        </template>
      </Column>

      <Column header="Заметка" class="w-48">
        <template #body="{ data }: { data: Application }">
          <StatusTag v-if="data.error_code" :code="data.error_code" kind="error_code" />
          <span v-else class="text-slate-400">—</span>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
