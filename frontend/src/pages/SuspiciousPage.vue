<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { ShieldAlert, ShieldOff } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { unmarkSuspicious } from '@/api/vacancies'
import EmptyState from '@/components/EmptyState.vue'
import HHLink from '@/components/HHLink.vue'
import SalaryCell from '@/components/SalaryCell.vue'
import { useMutate, useVacancies } from '@/queries'
import { useUiStore } from '@/stores/ui'
import type { VacancyFilters, VacancyRow } from '@/schemas/vacancy'

const router = useRouter()
const toast = useToast()
const ui = useUiStore()

const filters = computed<VacancyFilters | null>(() =>
  ui.resumeId === null ? null : { resume_id: ui.resumeId, only_suspicious: true, per_page: 100 }
)
const { data, isPending } = useVacancies(filters)

const unmark = useMutate(['vacancies'], (id: number) => unmarkSuspicious(id, ui.resumeId ?? 0))

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

function reasons(row: VacancyRow): string[] {
  return row.skip_details ? row.skip_details.split('; ') : []
}
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else-if="(data?.items.length ?? 0) === 0" class="pt-14">
    <EmptyState
      :icon="ShieldAlert"
      title="Подозрительных нет"
      hint="Вакансии с признаками развода не выбрасываются, а попадают сюда, чтобы их можно было просмотреть глазами."
    />
  </div>

  <div v-else class="max-w-3xl space-y-2">
    <p class="mb-3 max-w-prose text-[13px] leading-relaxed text-slate-600">
      Бот на эти вакансии не откликается. Если какая-то на самом деле нормальная — снимите пометку,
      и она вернётся в общий поток.
    </p>

    <article
      v-for="row in data?.items ?? []"
      :key="row.id"
      class="rounded-[14px] border border-red-200 bg-white p-4"
    >
      <div class="flex items-start gap-3">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="text-[14px] font-medium text-slate-800 hover:underline"
              @click="router.push(`/vacancies/${String(row.id)}`)"
            >
              {{ row.title }}
            </button>
            <HHLink :url="row.url" />
          </div>
          <div class="mt-0.5 flex flex-wrap gap-x-3 text-[12.5px] text-slate-600">
            <span>{{ row.company_name ?? 'Компания не указана' }}</span>
            <SalaryCell
              :from="row.salary_from"
              :to="row.salary_to"
              :currency="row.currency"
              :gross="row.salary_gross"
            />
          </div>
          <ul v-if="reasons(row).length" class="mt-2 space-y-0.5 pl-4 text-[12.5px] text-red-800">
            <li v-for="reason in reasons(row)" :key="reason" class="list-disc">{{ reason }}</li>
          </ul>
        </div>
        <Button
          size="small"
          severity="secondary"
          outlined
          label="Это нормальная"
          @click="unmark.mutate(row.id, { onError: fail })"
        >
          <template #icon><ShieldOff class="mr-1.5 size-3.5" /></template>
        </Button>
      </div>
    </article>
  </div>
</template>
