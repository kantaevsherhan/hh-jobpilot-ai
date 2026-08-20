<script setup lang="ts">
import { computed } from 'vue'
import { KeyRound, ThumbsDown, ThumbsUp } from 'lucide-vue-next'
import { analysisSchema, type Analysis } from '@/schemas/vacancy'

const props = defineProps<{
  raw: Record<string, unknown> | null
  hiddenInstructions: unknown[]
}>()

const analysis = computed<Analysis | null>(() => {
  if (!props.raw) return null
  const parsed = analysisSchema.safeParse(props.raw)
  return parsed.success ? parsed.data : null
})

const groups = computed(() => {
  const value = analysis.value
  if (!value) return []
  return [
    { title: 'Совпало', items: value.matched_skills ?? [], tone: 'bg-teal-700/10 text-teal-900' },
    { title: 'Не хватает', items: value.missing_skills ?? [], tone: 'bg-slate-100 text-slate-700' },
    {
      title: 'Критично отсутствует',
      items: value.critical_missing ?? [],
      tone: 'bg-red-100 text-red-900'
    }
  ].filter((group) => group.items.length > 0)
})

const instructions = computed(() => props.hiddenInstructions.map((item) => String(item)))
</script>

<template>
  <div v-if="analysis === null" class="text-[13px] text-slate-500">
    Вакансия ещё не анализировалась.
  </div>

  <div v-else class="space-y-4">
    <!-- Скрытые инструкции идут первыми: их пропуск и есть главная причина отказов -->
    <section
      v-if="instructions.length"
      class="rounded-[12px] border border-amber-300 bg-amber-50 px-4 py-3"
    >
      <div class="flex items-center gap-2">
        <KeyRound class="size-4 text-amber-700" />
        <h4 class="text-[13px] font-semibold text-amber-900">Скрытые инструкции работодателя</h4>
      </div>
      <ul class="mt-1.5 space-y-1 pl-6 text-[13px] text-amber-900">
        <li v-for="item in instructions" :key="item" class="list-disc">{{ item }}</li>
      </ul>
    </section>

    <p v-if="analysis.reason" class="max-w-prose text-[13.5px] leading-relaxed text-slate-700">
      {{ analysis.reason }}
    </p>

    <div v-if="analysis.score_breakdown" class="flex flex-wrap gap-x-6 gap-y-1.5">
      <div v-for="(value, key) in analysis.score_breakdown" :key="key">
        <span class="text-[12px] text-slate-500">{{ key }}</span>
        <span class="ml-1.5 font-mono text-[13px] tabular-nums text-slate-800">{{ value }}</span>
      </div>
    </div>

    <div v-for="group in groups" :key="group.title">
      <p class="mb-1.5 text-[12px] font-medium text-slate-500">{{ group.title }}</p>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="item in group.items"
          :key="item"
          class="rounded-full px-2.5 py-0.5 text-[12.5px]"
          :class="group.tone"
        >
          {{ item }}
        </span>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <section v-if="analysis.green_flags?.length">
        <div class="mb-1.5 flex items-center gap-1.5">
          <ThumbsUp class="size-3.5 text-teal-700" />
          <p class="text-[12px] font-medium text-slate-500">Плюсы</p>
        </div>
        <ul class="space-y-1 pl-4 text-[13px] text-slate-700">
          <li v-for="item in analysis.green_flags" :key="item" class="list-disc">{{ item }}</li>
        </ul>
      </section>

      <section v-if="analysis.red_flags?.length">
        <div class="mb-1.5 flex items-center gap-1.5">
          <ThumbsDown class="size-3.5 text-red-700" />
          <p class="text-[12px] font-medium text-slate-500">Настораживает</p>
        </div>
        <ul class="space-y-1 pl-4 text-[13px] text-slate-700">
          <li v-for="item in analysis.red_flags" :key="item" class="list-disc">{{ item }}</li>
        </ul>
      </section>
    </div>
  </div>
</template>
