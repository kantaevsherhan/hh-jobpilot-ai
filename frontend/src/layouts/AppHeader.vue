<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { Circle, CircleHelp, Pause, Play, Square } from 'lucide-vue-next'
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
const router = useRouter()
const ui = useUiStore()
const modeHelp = ref(false)

const { data: resumes, isPending: resumesPending } = useResumes()
const { data: botStatus } = useBotStatus()
const { data: browserStatus } = useBrowserStatus()
const { data: providers } = useProviders()
const { start, pause, resume, stop } = useBotControls()

const pageTitle = computed(() => (typeof route.meta.title === 'string' ? route.meta.title : ''))

const resumeOptions = computed(() =>
  (resumes.value ?? []).map((item) => ({ label: item.name, value: item.id }))
)

// Резюме одно — выбирать его руками бессмысленно. И если выбранное удалили,
// селектор не должен остаться указывающим в пустоту
watch(
  resumes,
  (list) => {
    if (!list?.length) return
    const exists = list.some((item) => item.id === ui.resumeId)
    if (!exists) ui.resumeId = list.length === 1 ? list[0].id : null
  },
  { immediate: true }
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
    {
      label: 'Модели',
      text: modelsReady ? 'добавлены · проверьте подключение' : 'не настроены',
      on: modelsReady
    }
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
  // Прогон идёт от аккаунта пользователя: без входа в HH запускать нечего
  if (browserStatus.value?.state !== 'READY') {
    toast.add({
      severity: 'warn',
      summary: 'Нужен вход в hh.kz',
      detail: 'Откройте «Настройки → Браузер», войдите в свой аккаунт и нажмите «Проверить вход».',
      life: 9000
    })
    void router.push('/settings/browser')
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
    header: 'Включить реальную отправку',
    message:
      'В режиме реальной отправки бот сможет отправлять отклики работодателям. Сначала проверьте результаты пробного прогона и подготовленные письма.',
    acceptLabel: 'Включить отправку',
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
  <header
    class="flex h-14 shrink-0 items-center gap-3 overflow-x-auto border-b border-slate-200 bg-white px-5"
  >
    <h1 class="shrink-0 text-[15px] font-semibold whitespace-nowrap text-slate-800">
      {{ pageTitle }}
    </h1>

    <Select
      v-model="ui.resumeId"
      data-tour="resume-picker"
      :options="resumeOptions"
      option-label="label"
      option-value="value"
      :loading="resumesPending"
      placeholder="Резюме не выбрано"
      size="small"
      class="w-52 shrink-0"
    />

    <SelectButton
      data-tour="bot-mode"
      :model-value="ui.botMode"
      :options="BOT_MODES"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      size="small"
      class="shrink-0 whitespace-nowrap"
      @update:model-value="ui.botMode = $event as BotMode"
    />

    <button
      data-tour="runtime-mode"
      type="button"
      class="shrink-0 rounded-full px-3 py-1 text-[11.5px] font-semibold tracking-wide whitespace-nowrap transition-colors"
      :class="
        ui.isLive
          ? 'bg-red-600 text-white hover:bg-red-700'
          : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
      "
      @click="switchRuntime(ui.isLive ? 'DRY_RUN' : 'LIVE')"
    >
      {{ ui.isLive ? 'Реальная отправка' : 'Пробный режим' }}
    </button>
    <button
      type="button"
      class="-ml-1 flex size-6 shrink-0 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-800"
      aria-label="Что означает пробный режим"
      @click="modeHelp = true"
    >
      <CircleHelp class="size-4" />
    </button>

    <div class="ml-auto flex shrink-0 items-center gap-3">
      <div
        v-for="item in indicators"
        :key="item.label"
        v-tooltip.bottom="`${item.label}: ${item.text}`"
        class="flex cursor-default items-center gap-1.5 text-[12px] whitespace-nowrap"
      >
        <Circle
          class="size-2.5 shrink-0"
          :class="item.on ? 'fill-teal-600 text-teal-600' : 'fill-slate-300 text-slate-300'"
        />
        <span :class="item.on ? 'text-slate-700' : 'text-slate-400'">{{ item.label }}</span>
      </div>

      <div class="flex shrink-0 items-center gap-1.5">
        <Button
          v-if="!isBusy"
          data-tour="launch"
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
  <Dialog
    v-model:visible="modeHelp"
    modal
    header="Режим отправки"
    class="w-[min(440px,calc(100vw-32px))]"
  >
    <div class="space-y-3 text-[13px] leading-relaxed text-slate-700">
      <p>
        <strong>Пробный режим</strong> — бот ищет и анализирует вакансии, готовит письмо и может
        заполнить форму, но не отправляет отклик работодателю.
      </p>
      <p>
        <strong>Реальная отправка</strong> — отклики могут уйти работодателям. Включайте её после
        проверки результатов пробного прогона.
      </p>
      <p class="text-slate-500">
        Ручной, полуавтоматический и автоматический режимы рядом определяют, сколько решений
        принимает бот сам.
      </p>
    </div>
  </Dialog>
</template>
