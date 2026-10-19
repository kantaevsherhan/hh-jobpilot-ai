<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Slider from 'primevue/slider'
import { useToast } from 'primevue/usetoast'
import { RotateCcw, Save } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { useFormErrors } from '@/composables/useFormErrors'
import { usePatchSettings, useSettings } from '@/queries'
import { deepCopy } from '@/utils/clone'
import type { AppSettings } from '@/api/settings'

const RANGE_LABELS: Record<string, string> = {
  page_load: 'Загрузка страницы',
  between_vacancies: 'Между вакансиями',
  between_search_pages: 'Между страницами поиска',
  before_open_form: 'Перед открытием формы',
  before_submit: 'Перед отправкой',
  after_apply: 'После отклика',
  typing_per_char: 'Ввод символа',
  on_error: 'После ошибки'
}

const DEFAULTS: AppSettings['delays'] = {
  speed_multiplier: 1.0,
  long_pause_every: 12,
  long_pause_range: [45, 120],
  ranges: {
    page_load: [1.0, 2.5],
    between_vacancies: [3, 8],
    between_search_pages: [2, 5],
    before_open_form: [2, 4],
    before_submit: [2, 5],
    after_apply: [10, 20],
    typing_per_char: [0.01, 0.04],
    on_error: [3, 10]
  }
}

const toast = useToast()
const { data: settings, isPending } = useSettings()
const patch = usePatchSettings()

const delays = ref<AppSettings['delays']>(deepCopy(DEFAULTS))
const limits = ref({
  max_applications_per_run: 20,
  max_applications_per_day: 30,
  max_consecutive_errors: 5
})

watch(
  settings,
  (value) => {
    if (!value) return
    delays.value = deepCopy(value.delays)
    limits.value = { ...value.limits }
  },
  { immediate: true }
)

const invalidRanges = computed(() =>
  Object.entries(delays.value.ranges)
    .filter(([, [min, max]]) => min <= 0 || max <= 0 || min > max)
    .map(([key]) => RANGE_LABELS[key] ?? key)
)

const longPauseInvalid = computed(() => {
  const [min, max] = delays.value.long_pause_range
  return min <= 0 || max <= 0 || min > max
})

const { validate } = useFormErrors(() => ({
  ranges: invalidRanges.value.length
    ? `Проверьте диапазоны: ${invalidRanges.value.join(', ')}`
    : undefined,
  longPause: longPauseInvalid.value ? 'Проверьте диапазон длинной паузы' : undefined
}))

/** Та же формула, что в бэкенде: показать, во что превратятся настройки. */
const estimate = computed(() => {
  const [minBetween, maxBetween] = delays.value.ranges.between_vacancies
  const [minLoad, maxLoad] = delays.value.ranges.page_load
  const perVacancy =
    ((minBetween + maxBetween) / 2 + (minLoad + maxLoad) / 2) * delays.value.speed_multiplier + 120
  const breaks =
    delays.value.long_pause_every > 0 ? Math.floor(25 / delays.value.long_pause_every) : 0
  const [minPause, maxPause] = delays.value.long_pause_range
  const total =
    25 * perVacancy + breaks * ((minPause + maxPause) / 2) * delays.value.speed_multiplier
  return Math.max(1, Math.round(total / 60))
})

function save() {
  if (!validate()) return
  patch.mutate(
    { delays: delays.value, limits: limits.value },
    {
      onSuccess: () => {
        toast.add({
          severity: 'success',
          summary: 'Сохранено',
          detail: 'Применится со следующей задачи в очереди',
          life: 4000
        })
      },
      onError: (error: unknown) => {
        toast.add({
          severity: 'error',
          summary: 'Не сохранилось',
          detail: toMessage(error),
          life: 6000
        })
      }
    }
  )
}

function reset() {
  delays.value = deepCopy(DEFAULTS)
}
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else class="mx-auto w-full max-w-5xl pb-10">
    <p class="mb-4 max-w-prose text-[13px] leading-relaxed text-slate-600">
      Каждая пауза задаётся диапазоном, фактическое значение выбирается случайно внутри него. Это
      ограничение нагрузки на чужой сервер, а не маскировка: ровные интервалы бьют по HH одинаковыми
      пачками.
    </p>

    <section class="rounded-[14px] border border-slate-200 bg-white p-5">
      <label class="text-[13px] font-medium text-slate-700">Множитель скорости</label>
      <div class="mt-2 flex items-center gap-4">
        <Slider
          v-model="delays.speed_multiplier"
          :min="0.1"
          :max="3"
          :step="0.1"
          class="min-w-0 flex-1"
        />
        <span class="w-12 shrink-0 text-right text-[13px] tabular-nums text-slate-800">
          {{ delays.speed_multiplier.toFixed(1) }}
        </span>
      </div>
      <p class="mt-1.5 text-[12px] text-slate-500">
        Умножает все задержки сразу. Ниже 0.1 не опускается — обнулить паузы нельзя.
      </p>
    </section>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Задержки, секунды</h3>
      <div class="space-y-2">
        <div
          v-for="(range, key) in delays.ranges"
          :key="key"
          class="grid grid-cols-[1fr_88px_88px] items-center gap-3"
        >
          <span class="text-[13px] text-slate-700">{{ RANGE_LABELS[key] ?? key }}</span>
          <InputNumber
            v-model="range[0]"
            size="small"
            :min-fraction-digits="key === 'typing_per_char' ? 2 : 0"
            :max-fraction-digits="2"
            :step="key === 'typing_per_char' ? 0.01 : 1"
            fluid
            class="w-full"
          />
          <InputNumber
            v-model="range[1]"
            size="small"
            :min-fraction-digits="key === 'typing_per_char' ? 2 : 0"
            :max-fraction-digits="2"
            :step="key === 'typing_per_char' ? 0.01 : 1"
            fluid
            class="w-full"
          />
        </div>
      </div>

      <div
        class="mt-4 grid grid-cols-[1fr_88px_88px] items-center gap-3 border-t border-slate-200 pt-4"
      >
        <span class="text-[13px] text-slate-700">
          Длинная пауза каждые
          <InputNumber
            v-model="delays.long_pause_every"
            size="small"
            :min="0"
            :max="100"
            class="mx-1 w-16"
          />
          вакансий
        </span>
        <InputNumber v-model="delays.long_pause_range[0]" size="small" fluid class="w-full" />
        <InputNumber v-model="delays.long_pause_range[1]" size="small" fluid class="w-full" />
      </div>

      <Message
        v-if="invalidRanges.length || longPauseInvalid"
        severity="error"
        size="small"
        class="mt-3"
      >
        «От» не может быть больше «до», и обе границы должны быть больше нуля:
        {{ [...invalidRanges, ...(longPauseInvalid ? ['длинная пауза'] : [])].join(', ') }}
      </Message>

      <p v-else class="mt-3 text-[12.5px] text-slate-500">
        Прогон на 25 вакансий займёт примерно {{ estimate }} минут при текущих настройках.
      </p>
    </section>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Лимиты</h3>
      <div class="space-y-2.5">
        <div class="grid grid-cols-[1fr_120px] items-center gap-3">
          <span class="text-[13px] text-slate-700">Откликов за один прогон</span>
          <InputNumber
            v-model="limits.max_applications_per_run"
            size="small"
            :min="1"
            :max="200"
            fluid
            class="w-full"
          />
        </div>
        <div class="grid grid-cols-[1fr_120px] items-center gap-3">
          <span class="text-[13px] text-slate-700">Откликов за сутки</span>
          <InputNumber
            v-model="limits.max_applications_per_day"
            size="small"
            :min="1"
            :max="500"
            fluid
            class="w-full"
          />
        </div>
        <div class="grid grid-cols-[1fr_120px] items-center gap-3">
          <span class="text-[13px] text-slate-700">Ошибок подряд до остановки</span>
          <InputNumber
            v-model="limits.max_consecutive_errors"
            size="small"
            :min="1"
            :max="50"
            fluid
            class="w-full"
          />
        </div>
      </div>
    </section>

    <div class="mt-4 flex gap-2">
      <Button size="small" severity="secondary" outlined label="Сбросить к дефолтам" @click="reset">
        <template #icon><RotateCcw class="mr-1.5 size-3.5" /></template>
      </Button>
      <Button
        class="ml-auto"
        size="small"
        label="Сохранить"
        :loading="patch.isPending.value"
        @click="save"
      >
        <template #icon><Save class="mr-1.5 size-4" /></template>
      </Button>
    </div>
  </div>
</template>
