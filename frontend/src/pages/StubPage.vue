<script setup lang="ts">
import { Construction } from 'lucide-vue-next'

defineProps<{ title: string; phase: string }>()
</script>

<template>
  <div class="mx-auto max-w-lg pt-16 text-center">
    <Construction class="mx-auto size-7 text-slate-400" />
    <h2 class="mt-3 text-lg font-semibold tracking-tight text-slate-800">{{ title }}</h2>
    <p class="mt-1.5 text-[13.5px] leading-relaxed text-slate-500">
      Экран появится в фазе {{ phase }}. Порядок фаз — в §31 технического задания.
    </p>
  </div>
</template>
