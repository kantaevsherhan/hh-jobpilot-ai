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

  <div v-else class="mx-auto w-full max-w-5xl pb-10">
    <section class="rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="text-[13.5px] font-semibold text-slate-800">Курсы валют</h3>
      <p class="mt-1 mb-4 max-w-prose text-[12.5px] leading-relaxed text-slate-500">
        Сколько тенге стоит одна единица валюты. Правятся руками раз в месяц — за курсом в интернет
        приложение не ходит. Если курса нет, вакансия не отсекается, а идёт дальше с пометкой.
      </p>

      <div class="flex flex-wrap gap-3">
        <div v-for="(_, code) in rates" :key="code" class="w-28">
          <label class="mb-1 block text-[11.5px] tracking-wide text-slate-500">
            {{ code }}
          </label>
          <InputNumber
            v-model="rates[code]"
            size="small"
            fluid
            :min-fraction-digits="1"
            :max-fraction-digits="2"
          />
        </div>
      </div>

      <div class="mt-5 border-t border-slate-200 pt-4">
        <label class="text-[13px] font-medium text-slate-700">Ставка налога</label>
        <p class="mt-0.5 mb-2 max-w-prose text-[12px] leading-relaxed text-slate-500">
          Зарплата «до вычета» умножается на (1 − ставка) перед сравнением с минимумом
        </p>
        <div class="w-28">
          <InputNumber
            v-model="taxRate"
            size="small"
            fluid
            :min="0"
            :max="0.6"
            :step="0.01"
            :min-fraction-digits="2"
          />
        </div>
      </div>
    </section>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="text-[13.5px] font-semibold text-slate-800">Модель и письма</h3>

      <div class="mt-4">
        <label class="text-[13px] font-medium text-slate-700">Обрезать описание, символов</label>
        <p class="mt-0.5 mb-2 max-w-prose text-[12px] leading-relaxed text-slate-500">
          Контекст локальной модели — 8192 токена, и его делят между собой описание вакансии,
          выжимка резюме и инструкции
        </p>
        <div class="w-32">
          <InputNumber
            v-model="llm.max_vacancy_chars"
            size="small"
            fluid
            :min="1000"
            :max="20000"
          />
        </div>
      </div>

      <div class="mt-5 border-t border-slate-200 pt-4">
        <label class="text-[13px] font-medium text-slate-700">Длина письма, символов</label>
        <p class="mt-0.5 mb-2 max-w-prose text-[12px] leading-relaxed text-slate-500">
          Передаётся в промпт и проверяется после генерации
        </p>
        <div class="flex items-center gap-2">
          <div class="w-28">
            <InputNumber v-model="llm.letter_min_chars" size="small" fluid :min="200" />
          </div>
          <span class="text-[13px] text-slate-400">—</span>
          <div class="w-28">
            <InputNumber v-model="llm.letter_max_chars" size="small" fluid :min="300" />
          </div>
        </div>
      </div>
    </section>

    <section class="mt-4 rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="text-[13.5px] font-semibold text-slate-800">Вопросы работодателя</h3>

      <div class="mt-3 flex items-start gap-3">
        <ToggleSwitch
          v-model="answerQuestions"
          input-id="answer-questions"
          class="mt-0.5 shrink-0"
        />
        <div class="min-w-0">
          <label
            for="answer-questions"
            class="cursor-pointer text-[13px] font-medium text-slate-800"
          >
            Отвечать на вопросы в форме отклика
          </label>
          <p class="mt-1 max-w-prose text-[12.5px] leading-relaxed text-slate-500">
            Пока выключено, вакансии с вопросами уходят в «Нужны данные». Личные данные — паспорт,
            ИИН, адрес, реквизиты — не заполняются никогда, независимо от этой настройки.
          </p>
        </div>
      </div>

      <Message v-if="answerQuestions" severity="warn" size="small" class="mt-3">
        Модель отвечает на вопрос о кандидате, только если ответ выводится из резюме или Allowed
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
