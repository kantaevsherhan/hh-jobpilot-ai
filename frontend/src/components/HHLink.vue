<script setup lang="ts">
import { ExternalLink } from 'lucide-vue-next'

defineProps<{ url: string; label?: string }>()
</script>

<template>
  <a
    v-tooltip.top="'Открыть на hh.kz'"
    :href="url"
    target="_blank"
    rel="noopener"
    class="inline-flex items-center gap-1 text-teal-700 no-underline hover:underline"
    @click.stop
  >
    <span v-if="label">{{ label }}</span>
    <ExternalLink class="size-3.5 shrink-0" />
  </a>
</template>
