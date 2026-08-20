<script setup lang="ts">
import { computed } from 'vue'
import { useDictionaries } from '@/queries'

const props = defineProps<{ code: string | null; kind?: string }>()

const { data: dictionaries } = useDictionaries()

const label = computed(() => {
  if (!props.code) return '—'
  const dictionary = dictionaries.value?.[props.kind ?? 'vacancy_status']
  return dictionary?.[props.code] ?? props.code
})

/** Цвет несёт смысл: зелёный — дошло до отклика, красный — ошибка, янтарь — ждёт человека. */
const tone = computed(() => {
  switch (props.code) {
    case 'APPLIED':
    case 'LETTER_READY':
    case 'RECOMMENDED':
      return 'bg-teal-700/10 text-teal-900'
    case 'REVIEW_REQUIRED':
    case 'NEEDS_DATA':
    case 'NEEDS_USER_ACTION':
    case 'APPLY_PREPARED':
      return 'bg-amber-100 text-amber-900'
    case 'SUSPICIOUS':
    case 'APPLY_FAILED':
    case 'ANALYSIS_FAILED':
    case 'PARSE_FAILED':
    case 'APPLY_UNKNOWN':
      return 'bg-red-100 text-red-900'
    case 'FILTERED_OUT':
    case 'REJECTED_BY_AI':
    case 'SKIPPED_BY_USER':
    case 'VACANCY_CLOSED':
      return 'bg-slate-100 text-slate-600'
    default:
      return 'bg-slate-100 text-slate-700'
  }
})
</script>

<template>
  <span class="rounded-full px-2 py-0.5 text-[11.5px] font-medium whitespace-nowrap" :class="tone">
    {{ label }}
  </span>
</template>
