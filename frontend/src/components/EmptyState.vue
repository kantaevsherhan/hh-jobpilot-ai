<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ icon: Component; title: string; hint?: string }>()
</script>

<template>
  <div class="px-6 py-12 text-center">
    <component :is="icon" class="mx-auto size-6 text-slate-400" />
    <p class="mt-2.5 text-[13.5px] font-medium text-slate-700">{{ title }}</p>
    <p v-if="hint" class="mx-auto mt-1 max-w-sm text-[12.5px] leading-relaxed text-slate-500">
      {{ hint }}
    </p>
    <slot />
  </div>
</template>
