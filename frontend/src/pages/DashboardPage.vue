<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import { FileText, Plus } from 'lucide-vue-next'
import { useResumes } from '@/queries/resumes'

const { data: resumes, isPending } = useResumes()
const count = computed(() => resumes.value?.length ?? 0)
</script>

<template>
  <div class="max-w-3xl">
    <h2 class="text-xl font-semibold tracking-tight text-slate-900">
      Приложение готовится к работе
    </h2>
    <p class="mt-2 max-w-prose text-[14px] leading-relaxed text-slate-600">
      Собран каркас: база, API и экран резюме. Счётчики вакансий, откликов и прогонов появятся,
      когда заработают сбор и анализ — фазы 4 и 6.
    </p>

    <div class="mt-6 rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="flex items-start gap-3">
        <FileText class="mt-0.5 size-5 shrink-0 text-teal-700" />
        <div class="min-w-0 flex-1">
          <p class="text-[13.5px] font-medium text-slate-800">Резюме</p>
          <p class="mt-0.5 text-[13px] text-slate-500">
            <span v-if="isPending">загружается…</span>
            <span v-else-if="count === 0"
              >Ни одного не создано. С него начинается всё остальное.</span
            >
            <span v-else>Создано: {{ count }}</span>
          </p>
        </div>
        <RouterLink to="/resumes">
          <Button
            size="small"
            :label="count === 0 ? 'Создать' : 'Открыть'"
            severity="secondary"
            outlined
          >
            <template #icon><Plus v-if="count === 0" class="mr-1.5 size-4" /></template>
          </Button>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
