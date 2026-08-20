<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ score: number | null }>()

const tone = computed(() => {
  if (props.score === null) return 'text-slate-400'
  if (props.score >= 90) return 'text-teal-800'
  if (props.score >= 75) return 'text-slate-800'
  return 'text-slate-400'
})
</script>

<template>
  <span class="font-mono text-[13px] tabular-nums" :class="tone">
    {{ score ?? '—' }}
  </span>
</template>
