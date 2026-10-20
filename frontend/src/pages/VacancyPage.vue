<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { ArrowLeft, Send, ShieldOff, SkipForward } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { applyToVacancy, skipVacancy, unmarkSuspicious } from '@/api/vacancies'
import AnalysisPanel from '@/components/AnalysisPanel.vue'
import HHLink from '@/components/HHLink.vue'
import LetterPanel from '@/components/LetterPanel.vue'
import SalaryCell from '@/components/SalaryCell.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useLetters, useMutate, useVacancy } from '@/queries'
import { useUiStore } from '@/stores/ui'
import { formatDate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const ui = useUiStore()

const vacancyId = computed(() => Number(route.params.id))
const { data: vacancy, isPending } = useVacancy(vacancyId, () => ui.resumeId)
const { data: letters } = useLetters(vacancyId, () => ui.resumeId)

const selectedLetter = computed(() => letters.value?.find((letter) => letter.is_selected) ?? null)
const applying = ref(false)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 8000 })
}

const skip = useMutate(['vacancy', 'vacancies'], () =>
  skipVacancy(vacancyId.value, ui.resumeId ?? 0)
)
const unmark = useMutate(['vacancy', 'vacancies'], () =>
  unmarkSuspicious(vacancyId.value, ui.resumeId ?? 0)
)

async function send(runtimeMode: 'DRY_RUN' | 'LIVE') {
  if (ui.resumeId === null) return
  applying.value = true
  try {
    const result = await applyToVacancy(vacancyId.value, {
      resume_id: ui.resumeId,
      letter_id: selectedLetter.value?.id ?? null,
      runtime_mode: runtimeMode
    })
    toast.add({ severity: 'success', summary: 'Отклик', detail: result.message, life: 8000 })
  } catch (error) {
    fail(error)
  } finally {
    applying.value = false
  }
}

function confirmLive() {
  confirm.require({
    header: 'Отправить отклик',
    message: `Отклик на «${vacancy.value?.title ?? ''}» уйдёт работодателю. Повторно откликнуться на эту вакансию будет нельзя.`,
    acceptLabel: 'Отправить',
    rejectLabel: 'Отмена',
    acceptProps: { size: 'small' },
    rejectProps: { severity: 'secondary', outlined: true, size: 'small' },
    accept: () => void send('LIVE')
  })
}

const alreadyApplied = computed(() => vacancy.value?.applied_at !== null)
const factCheckFailed = computed(() => selectedLetter.value?.fact_check_passed === false)
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else-if="vacancy" class="mx-auto w-full max-w-6xl pb-10">
    <div class="mb-4 flex items-start gap-3">
      <button
        type="button"
        class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-[9px] text-slate-500 hover:bg-slate-100"
        @click="router.back()"
      >
        <ArrowLeft class="size-4" />
      </button>

      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-lg font-semibold tracking-tight text-slate-900">{{ vacancy.title }}</h2>
          <HHLink :url="vacancy.url" label="hh.kz" />
        </div>
        <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-slate-600">
          <span>{{ vacancy.company_name ?? 'Компания не указана' }}</span>
          <SalaryCell
            :from="vacancy.salary_from"
            :to="vacancy.salary_to"
            :currency="vacancy.currency"
            :gross="vacancy.salary_gross"
          />
          <StatusTag :code="vacancy.work_format" kind="work_format" />
          <span v-if="vacancy.area">{{ vacancy.area }}</span>
          <span class="text-slate-400">найдена {{ formatDate(vacancy.first_seen_at) }}</span>
        </div>
      </div>

      <div class="flex shrink-0 items-center gap-2">
        <ScoreBadge :score="vacancy.score" />
        <StatusTag :code="vacancy.status" />
      </div>
    </div>

    <Message v-if="vacancy.is_closed" severity="warn" size="small" class="mb-3">
      Вакансия в архиве на HH.
    </Message>

    <Message v-if="alreadyApplied" severity="success" size="small" class="mb-3">
      Отклик отправлен {{ formatDate(vacancy.applied_at) }}. Повторный невозможен.
    </Message>

    <Message v-if="vacancy.is_suspicious" severity="error" size="small" class="mb-3">
      <p class="font-medium">Похоже на развод</p>
      <ul class="mt-1 space-y-0.5 pl-4">
        <li v-for="reason in vacancy.suspicious_reasons" :key="String(reason)" class="list-disc">
          {{ reason }}
        </li>
      </ul>
      <Button
        class="mt-2"
        size="small"
        severity="secondary"
        outlined
        label="Это нормальная вакансия"
        @click="unmark.mutate(undefined, { onError: fail })"
      >
        <template #icon><ShieldOff class="mr-1.5 size-3.5" /></template>
      </Button>
    </Message>

    <div class="rounded-[14px] border border-slate-200 bg-white">
      <Tabs value="analysis">
        <TabList>
          <Tab value="analysis">Анализ</Tab>
          <Tab value="letter">Письмо</Tab>
          <Tab value="description">Описание</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="analysis">
            <AnalysisPanel
              :raw="vacancy.analysis_json"
              :hidden-instructions="vacancy.hidden_instructions"
            />
          </TabPanel>
          <TabPanel value="letter">
            <LetterPanel
              v-if="ui.resumeId !== null"
              :vacancy-id="vacancyId"
              :resume-id="ui.resumeId"
            />
          </TabPanel>
          <TabPanel value="description">
            <p class="text-[12px] text-slate-500">
              Язык описания: {{ vacancy.description_lang ?? 'не определён' }}
            </p>
            <pre
              class="mt-2 max-h-[32rem] overflow-auto text-[13px] leading-relaxed whitespace-pre-wrap text-slate-700"
              >{{ vacancy.description || 'Описание не сохранено — карточка не открывалась.' }}</pre>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <div class="mt-4 flex flex-wrap items-center gap-2">
      <Button
        size="small"
        severity="secondary"
        outlined
        label="Пропустить"
        @click="skip.mutate(undefined, { onError: fail })"
      >
        <template #icon><SkipForward class="mr-1.5 size-3.5" /></template>
      </Button>

      <div class="ml-auto flex gap-2">
        <Button
          size="small"
          severity="secondary"
          outlined
          label="Открыть на hh без отклика"
          :loading="applying"
          :disabled="alreadyApplied"
          @click="send('DRY_RUN')"
        />
        <Button
          size="small"
          severity="danger"
          label="Откликнуться"
          :loading="applying"
          :disabled="alreadyApplied || factCheckFailed"
          @click="confirmLive"
        >
          <template #icon><Send class="mr-1.5 size-3.5" /></template>
        </Button>
      </div>
    </div>

    <p v-if="factCheckFailed" class="mt-2 text-right text-[12px] text-red-700">
      Письмо не прошло проверку фактов — отправка заблокирована.
    </p>
  </div>
</template>
