<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Select from 'primevue/select'
import { Circle, CircleDot } from 'lucide-vue-next'
import { useResumes } from '@/queries/resumes'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const route = useRoute()
const { data: resumes, isPending } = useResumes()

const options = computed(() => (resumes.value ?? []).map((r) => ({ label: r.name, value: r.id })))

const pageTitle = computed(() => (typeof route.meta.title === 'string' ? route.meta.title : ''))

// Фазы 2-9 ещё не подключены, поэтому индикаторы пока показывают заведомое «нет».
// Как только появятся /bot/status и /browser/status, значения приедут оттуда.
const indicators = [
  { label: 'Бот', text: 'Не запущен', tone: 'idle' },
  { label: 'HH', text: 'Нет сессии', tone: 'idle' },
  { label: 'Модели', text: 'Не настроены', tone: 'idle' }
]
</script>

<template>
  <header class="flex h-14 shrink-0 items-center gap-5 border-b border-slate-200 bg-white px-5">
    <h1 class="text-[15px] font-semibold tracking-tight text-slate-800">{{ pageTitle }}</h1>

    <div class="flex items-center gap-2">
      <span class="text-[12px] text-slate-500">Резюме</span>
      <Select
        v-model="ui.resumeId"
        :options="options"
        option-label="label"
        option-value="value"
        :loading="isPending"
        placeholder="не выбрано"
        size="small"
        class="w-56"
      />
    </div>

    <div class="ml-auto flex items-center gap-4">
      <div class="flex items-center gap-1.5">
        <span class="text-[12px] text-slate-500">Режим</span>
        <span
          class="rounded-full bg-slate-200 px-2.5 py-0.5 text-[11px] font-semibold tracking-wide text-slate-700"
        >
          DRY_RUN
        </span>
      </div>

      <div
        v-for="item in indicators"
        :key="item.label"
        class="flex items-center gap-1.5 text-[12px] text-slate-500"
      >
        <component
          :is="item.tone === 'idle' ? Circle : CircleDot"
          class="size-3"
          :class="item.tone === 'idle' ? 'text-slate-300' : 'text-teal-600'"
        />
        <span class="text-slate-600">{{ item.label }}</span>
        <span class="text-slate-400">{{ item.text }}</span>
      </div>
    </div>
  </header>
</template>
