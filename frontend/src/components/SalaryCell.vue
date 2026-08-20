<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  from: number | null
  to: number | null
  currency: string | null
  gross: boolean | null
}>()

const SIGNS: Record<string, string> = { KZT: '₸', RUR: '₽', RUB: '₽', USD: '$', EUR: '€' }

// ru-RU разделяет разряды неразрывным пробелом — так «900 000» не переносится
// по строкам. Замена запятых осталась от прежней локали и ничего не делала
const format = (value: number) => value.toLocaleString('ru-RU')

const text = computed(() => {
  const sign = SIGNS[props.currency ?? ''] ?? props.currency ?? ''
  if (props.from && props.to) return `${format(props.from)}–${format(props.to)} ${sign}`
  if (props.from) return `от ${format(props.from)} ${sign}`
  if (props.to) return `до ${format(props.to)} ${sign}`
  return null
})
</script>

<template>
  <span v-if="text" class="whitespace-nowrap text-slate-700">
    {{ text }}
    <span v-if="gross" class="text-[11px] text-slate-400">до вычета</span>
  </span>
  <span v-else class="text-slate-400">не указана</span>
</template>
