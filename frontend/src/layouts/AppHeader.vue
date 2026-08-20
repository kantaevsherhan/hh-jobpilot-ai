<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { Circle, Pause, Play, Square } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { useBotStatus, useBotControls } from '@/queries'
import { useBrowserStatus } from '@/queries/browser'
import { useProviders } from '@/queries/llm'
import { useResumes } from '@/queries/resumes'
import { useUiStore } from '@/stores/ui'
import type { BotMode, RuntimeMode } from '@/stores/ui'

const BOT_MODES = [
  { value: 'MANUAL', label: 'Ручной' },
  { value: 'SEMI_AUTO', label: 'Полуавтомат' },
  { value: 'AUTO', label: 'Автомат' }
]

const toast = useToast()
const confirm = useConfirm()
const route = useRoute()
const ui = useUiStore()

const { data: resumes, isPending: resumesPending } = useResumes()
const { data: botStatus } = useBotStatus()
const { data: browserStatus } = useBrowserStatus()
const { data: providers } = useProviders()
const { start, pause, resume, stop } = useBotControls()

const pageTitle = computed(() => (typeof route.meta.title === 'string' ? route.meta.title : ''))

const resumeOptions = computed(() =>
  (resumes.value ?? []).map((item) => ({ label: item.name, value: item.id }))
)

const indicators = computed(() => {
  const botRunning = botStatus.value?.is_busy === true
  const hh = browserStatus.value?.state === 'READY'
  const modelsReady = (providers.value ?? []).some((provider) => provider.is_enabled)
  return [
    {
      label: 'Бот',
      text: botRunning ? (botStatus.value?.current_job ?? 'работает') : 'не запущен',
      on: botRunning
    },
    { label: 'HH', text: hh ? 'подключён' : 'нет сессии', on: hh },
    { label: 'Модели', text: modelsReady ? 'готовы' : 'не настроены', on: modelsReady }
  ]
})

const isPaused = computed(() => botStatus.value?.status === 'PAUSED')
const isBusy = computed(() => botStatus.value?.is_busy === true)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Бот', detail: toMessage(error), life: 8000 })
}

function launch() {
  if (ui.resumeId === null) {
    toast.add({ severity: 'warn', summary: 'Сначала выберите резюме', life: 4000 })
    return
  }
  start.mutate(
    { resume_id: ui.resumeId, mode: ui.botMode, runtime_mode: ui.runtimeMode },
    {
      onSuccess: () => {
        toast.add({ severity: 'success', summary: 'Прогон запущен', life: 3000 })
      },
      onError: fail
    }
  )
}

function switchRuntime(value: RuntimeMode) {
  if (value !== 'LIVE') {
    ui.runtimeMode = value
    return
  }
  confirm.require({
    header: 'Включить боевой режим',
    message:
      'В режиме LIVE отклики уходят работодателям по-настоящему. Перед этим стоит посмотреть несколько подготовленных писем.',
    acceptLabel: 'Включить LIVE',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger', size: 'small' },
    rejectProps: { severity: 'secondary', outlined: true, size: 'small' },
    accept: () => {
      ui.runtimeMode = 'LIVE'
    }
  })
}
</script>

<template>
  <header class="flex h-14 shrink-0 items-center gap-4 border-b border-slate-200 bg-white px-5">
    <h1 class="shrink-0 text-[15px] font-semibold tracking-tight text-slate-800">
      {{ pageTitle }}
    </h1>

    <Select
      v-model="ui.resumeId"
      :options="resumeOptions"
      option-label="label"
      option-value="value"
      :loading="resumesPending"
      placeholder="Резюме не выбрано"
      size="small"
      class="w-52"
    />

    <SelectButton
      :model-value="ui.botMode"
      :options="BOT_MODES"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      size="small"
      @update:model-value="ui.botMode = $event as BotMode"
    />

    <button
      type="button"
      class="rounded-full px-3 py-1 text-[11.5px] font-semibold tracking-wide transition-colors"
      :class="
        ui.isLive
          ? 'bg-red-600 text-white hover:bg-red-700'
          : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
      "
      @click="switchRuntime(ui.isLive ? 'DRY_RUN' : 'LIVE')"
    >
      {{ ui.runtimeMode }}
    </button>

    <div class="ml-auto flex items-center gap-4">
      <div
        v-for="item in indicators"
        :key="item.label"
        class="flex items-center gap-1.5 text-[12px]"
      >
        <Circle
          class="size-2.5"
          :class="item.on ? 'fill-teal-600 text-teal-600' : 'fill-slate-300 text-slate-300'"
        />
        <span class="text-slate-600">{{ item.label }}</span>
        <span class="text-slate-400">{{ item.text }}</span>
      </div>

      <div class="flex items-center gap-1.5">
        <Button
          v-if="!isBusy"
          size="small"
          severity="secondary"
          outlined
          label="Запустить"
          :loading="start.isPending.value"
          @click="launch"
        >
          <template #icon><Play class="mr-1.5 size-3.5" /></template>
        </Button>
        <template v-else>
          <Button
            size="small"
            severity="secondary"
            outlined
            :label="isPaused ? 'Продолжить' : 'Пауза'"
            :loading="pause.isPending.value || resume.isPending.value"
            @click="
              isPaused
                ? resume.mutate(undefined, { onError: fail })
                : pause.mutate(undefined, { onError: fail })
            "
          >
            <template #icon>
              <component :is="isPaused ? Play : Pause" class="mr-1.5 size-3.5" />
            </template>
          </Button>
          <Button
            size="small"
            severity="danger"
            outlined
            label="Стоп"
            :loading="stop.isPending.value"
            @click="stop.mutate(undefined, { onError: fail })"
          >
            <template #icon><Square class="mr-1.5 size-3.5" /></template>
          </Button>
        </template>
      </div>
    </div>
  </header>
</template>
