<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { CheckCircle2, PenLine, ShieldCheck, Sparkles, XCircle } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { generateLetter, runFactCheck, selectLetter, writeLetterManually } from '@/api/vacancies'
import { useLetters, useMutate } from '@/queries'
import { formatDateTime } from '@/utils/format'
import type { Letter } from '@/schemas/vacancy'

const props = defineProps<{ vacancyId: number; resumeId: number }>()

const toast = useToast()
const { data: letters, isPending } = useLetters(
  () => props.vacancyId,
  () => props.resumeId
)

const draft = ref('')
const instruction = ref('')

const selected = computed(() => letters.value?.find((letter) => letter.is_selected) ?? null)

watch(
  selected,
  (letter) => {
    draft.value = letter?.content ?? ''
  },
  { immediate: true }
)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 8000 })
}

const generate = useMutate(['letters', 'vacancy'], (payload: { instruction?: string }) =>
  generateLetter(props.vacancyId, { resume_id: props.resumeId, instruction: payload.instruction })
)
const saveManual = useMutate(['letters', 'vacancy'], (content: string) =>
  writeLetterManually(props.vacancyId, { resume_id: props.resumeId, content })
)
const pick = useMutate(['letters'], selectLetter)
const check = useMutate(['letters'], (letterId: number) => runFactCheck(letterId, props.resumeId))

const QUICK = [
  { label: 'Короче', instruction: 'Сделай письмо заметно короче, оставь только суть.' },
  { label: 'Более технично', instruction: 'Добавь технических деталей по стеку из резюме.' },
  { label: 'Более живо', instruction: 'Пиши живее и проще, без канцелярита.' }
]

function unsupported(letter: Letter): string[] {
  const value = letter.fact_check_json?.dictionary_unsupported
  return Array.isArray(value) ? value.map(String) : []
}

function missingInstructions(letter: Letter): string[] {
  const value = letter.fact_check_json?.instructions_missing
  return Array.isArray(value) ? value.map(String) : []
}
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <Button
        size="small"
        :label="selected ? 'Перегенерировать' : 'Сгенерировать'"
        :loading="generate.isPending.value"
        @click="generate.mutate({}, { onError: fail })"
      >
        <template #icon><Sparkles class="mr-1.5 size-4" /></template>
      </Button>
      <Button
        v-for="quick in QUICK"
        :key="quick.label"
        size="small"
        severity="secondary"
        outlined
        :label="quick.label"
        :disabled="!selected || generate.isPending.value"
        @click="generate.mutate({ instruction: quick.instruction }, { onError: fail })"
      />
      <div class="flex flex-1 gap-2">
        <InputText
          v-model="instruction"
          size="small"
          class="min-w-40 flex-1"
          placeholder="Своя инструкция для перегенерации"
        />
        <Button
          size="small"
          severity="secondary"
          outlined
          label="Применить"
          :disabled="!instruction.trim() || generate.isPending.value"
          @click="generate.mutate({ instruction }, { onError: fail })"
        />
      </div>
    </div>

    <p v-if="generate.isPending.value" class="text-[12.5px] text-slate-500">
      Модель пишет письмо. На локальной это около минуты.
    </p>

    <Textarea
      v-model="draft"
      class="w-full text-[13.5px] leading-relaxed"
      rows="14"
      placeholder="Можно написать письмо полностью самому — бот просто вставит этот текст в форму."
    />

    <div class="flex items-center gap-3">
      <span class="text-[12px] text-slate-500">{{ draft.length }} символов</span>
      <div class="ml-auto flex gap-2">
        <Button
          size="small"
          severity="secondary"
          outlined
          label="Сохранить как своё"
          :disabled="!draft.trim() || draft === selected?.content"
          :loading="saveManual.isPending.value"
          @click="saveManual.mutate(draft, { onError: fail })"
        >
          <template #icon><PenLine class="mr-1.5 size-3.5" /></template>
        </Button>
        <Button
          v-if="selected"
          size="small"
          severity="secondary"
          outlined
          label="Проверить факты"
          :loading="check.isPending.value"
          @click="check.mutate(selected.id, { onError: fail })"
        >
          <template #icon><ShieldCheck class="mr-1.5 size-3.5" /></template>
        </Button>
      </div>
    </div>

    <Message
      v-if="selected && unsupported(selected).length"
      severity="error"
      size="small"
      class="text-[12.5px]"
    >
      В письме есть то, чего нет в резюме: {{ unsupported(selected).join(', ') }}. Отправка
      заблокирована.
    </Message>

    <Message
      v-if="selected && missingInstructions(selected).length"
      severity="warn"
      size="small"
      class="text-[12.5px]"
    >
      Не выполнены условия работодателя: {{ missingInstructions(selected).join(', ') }}
    </Message>

    <section v-if="(letters?.length ?? 0) > 1">
      <p class="mb-2 text-[12px] font-medium text-slate-500">Версии</p>
      <div class="space-y-1.5">
        <button
          v-for="letter in letters"
          :key="letter.id"
          type="button"
          class="flex w-full items-center gap-3 rounded-[10px] border px-3 py-2 text-left text-[13px]"
          :class="
            letter.is_selected
              ? 'border-teal-700/40 bg-teal-700/5'
              : 'border-slate-200 hover:bg-slate-50'
          "
          @click="pick.mutate(letter.id, { onError: fail })"
        >
          <span class="font-mono text-[12px] text-slate-500">v{{ letter.version }}</span>
          <span class="text-slate-700">{{ letter.source }}</span>
          <span class="text-slate-400">{{ letter.char_count }} симв.</span>
          <component
            :is="letter.fact_check_passed === true ? CheckCircle2 : XCircle"
            v-if="letter.fact_check_passed !== null"
            class="size-4"
            :class="letter.fact_check_passed ? 'text-teal-700' : 'text-red-600'"
          />
          <span class="ml-auto text-[12px] text-slate-400">
            {{ formatDateTime(letter.created_at) }}
          </span>
        </button>
      </div>
    </section>
  </div>
</template>
