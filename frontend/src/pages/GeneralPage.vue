<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { Save } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { usePatchSettings, useSettings } from '@/queries'
import type { AppSettings } from '@/api/settings'

const toast = useToast()
const { data: settings, isPending } = useSettings()
const patch = usePatchSettings()

const rates = ref<Record<string, number>>({})
const taxRate = ref(0.1)
const llm = ref<AppSettings['llm']>({
  max_vacancy_chars: 6000,
  letter_min_chars: 900,
  letter_max_chars: 1400
})
const answerQuestions = ref(false)

watch(
  settings,
  (value) => {
    if (!value) return
    rates.value = { ...value.currency_rates }
    taxRate.value = value.tax_rate
    llm.value = { ...value.llm }
    answerQuestions.value = value.bot.answer_employer_questions
  },
  { immediate: true }
)

function save() {
  patch.mutate(
    {
      currency_rates: rates.value,
      tax_rate: taxRate.value,
      llm: llm.value,
      bot: { answer_employer_questions: answerQuestions.value }
    },
    {
      onSuccess: () => {
        toast.add({ severity: 'success', summary: 'Сохранено', life: 3000 })
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
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else class="max-w-2xl pb-10">
    <section class="rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="text-[13.5px] font-semibold text-slate-800">Курсы валют</h3>
      <p class="mt-1 mb-3 max-w-prose text-[12.5px] leading-relaxed text-slate-500">
        Сколько тенге стоит одна единица валюты. Правятся руками раз в месяц — за курсом в интернет
        приложение не ходит. Если курса нет, вакансия не отсекается, а идёт дальше с пометкой.
      </p>
      <div class="grid grid-cols-4 gap-3">
        <div v-for="(_, code) in rates" :key="code">
          <label class="mb-1 block font-mono text-[12px] text-slate-600">{{ code }}</label>
          <InputNumber
            v-model="rates[code]"
            size="small"
            class="w-full"
            :min-fraction-digits="1"
            :max-fraction-digits="2"
          />
        </div>
      </div>

      <div
        class="mt-4 grid grid-cols-[1fr_120px] items-center gap-3 border-t border-slate-200 pt-4"
      >
        <div>
          <span class="text-[13px] text-slate-700">Ставка налога</span>
          <p class="text-[12px] text-slate-500">
            Зарплата «до вычета» умножается на (1 − ставка) перед сравнением
          </p>
        </div>
        <InputNumber
          v-model="taxRate"
          size="small"
          class="w-full"
          :min="0"
          :max="0.6"
          :step="0.01"
          :min-fraction-digits="2"
        />
      </div>
    </section>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Модель и письма</h3>
      <div class="space-y-2.5">
        <div class="grid grid-cols-[1fr_120px] items-center gap-3">
          <div>
            <span class="text-[13px] text-slate-700">Обрезать описание, символов</span>
            <p class="text-[12px] text-slate-500">
              Контекст локальной модели — 8192 токена, его делят описание, выжимка и инструкции
            </p>
          </div>
          <InputNumber
            v-model="llm.max_vacancy_chars"
            size="small"
            class="w-full"
            :min="1000"
            :max="20000"
          />
        </div>
        <div class="grid grid-cols-[1fr_120px_120px] items-center gap-3">
          <span class="text-[13px] text-slate-700">Длина письма, символов</span>
          <InputNumber v-model="llm.letter_min_chars" size="small" class="w-full" :min="200" />
          <InputNumber v-model="llm.letter_max_chars" size="small" class="w-full" :min="300" />
        </div>
      </div>
    </section>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Вопросы работодателя</h3>
      <label class="flex items-start gap-3">
        <ToggleSwitch v-model="answerQuestions" class="mt-0.5" />
        <span class="text-[13px] leading-relaxed text-slate-700">
          Отвечать на вопросы в форме отклика
          <span class="mt-0.5 block text-[12.5px] text-slate-500">
            Пока выключено, вакансии с вопросами уходят в «Нужны данные». Личные данные — паспорт,
            ИИН, адрес, реквизиты — не заполняются никогда, независимо от этой настройки.
          </span>
        </span>
      </label>
      <Message v-if="answerQuestions" severity="warn" size="small" class="mt-3">
        Модель отвечает на вопрос о кандидате только если ответ выводится из резюме или Allowed
        Facts. Не выводится — отклик не отправляется.
      </Message>
    </section>

    <div class="mt-4 flex justify-end">
      <Button size="small" label="Сохранить" :loading="patch.isPending.value" @click="save">
        <template #icon><Save class="mr-1.5 size-4" /></template>
      </Button>
    </div>
  </div>
</template>
