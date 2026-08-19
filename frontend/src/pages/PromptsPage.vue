<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { RotateCcw, Save } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { usePatchPrompt, usePrompts, useResetPrompt } from '@/queries/llm'

const toast = useToast()
const { data: prompts, isPending } = usePrompts()
const patch = usePatchPrompt()
const reset = useResetPrompt()

const selectedKey = ref<string | null>(null)
const draft = ref('')

const selected = computed(() => (prompts.value ?? []).find((p) => p.key === selectedKey.value))

watch(
  prompts,
  (list) => {
    if (!list?.length) return
    selectedKey.value ??= list[0].key
    draft.value = list.find((p) => p.key === selectedKey.value)?.content ?? ''
  },
  { immediate: true }
)

function select(key: string) {
  selectedKey.value = key
  draft.value = (prompts.value ?? []).find((p) => p.key === key)?.content ?? ''
}

const changed = computed(
  () => selected.value !== undefined && draft.value !== selected.value.content
)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не сохранилось', detail: toMessage(error), life: 6000 })
}

function save() {
  if (!selectedKey.value) return
  patch.mutate(
    { key: selectedKey.value, content: draft.value },
    {
      onSuccess: () => {
        toast.add({ severity: 'success', summary: 'Промпт сохранён', life: 2500 })
      },
      onError: fail
    }
  )
}

function restore() {
  if (!selectedKey.value) return
  reset.mutate(selectedKey.value, {
    onSuccess: (prompt) => {
      draft.value = prompt.content
    },
    onError: fail
  })
}
</script>

<template>
  <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

  <div v-else class="grid max-w-6xl grid-cols-[240px_1fr] gap-5">
    <nav class="space-y-0.5">
      <button
        v-for="prompt in prompts"
        :key="prompt.key"
        type="button"
        class="block w-full rounded-[10px] px-3 py-2 text-left text-[13.5px] transition-colors"
        :class="
          prompt.key === selectedKey
            ? 'bg-teal-700/10 font-medium text-teal-900'
            : 'text-slate-600 hover:bg-slate-100'
        "
        @click="select(prompt.key)"
      >
        {{ prompt.title }}
        <span v-if="!prompt.is_default" class="ml-1 text-[11px] text-amber-700">изменён</span>
      </button>
    </nav>

    <section v-if="selected">
      <div class="mb-3 flex items-center gap-3">
        <div>
          <h2 class="text-[15px] font-semibold tracking-tight text-slate-900">
            {{ selected.title }}
          </h2>
          <p class="mt-0.5 font-mono text-[12px] text-slate-500">{{ selected.key }}</p>
        </div>
        <div class="ml-auto flex gap-2">
          <Button size="small" severity="secondary" outlined label="К дефолту" @click="restore">
            <template #icon><RotateCcw class="mr-1.5 size-3.5" /></template>
          </Button>
          <Button
            size="small"
            label="Сохранить"
            :disabled="!changed"
            :loading="patch.isPending.value"
            @click="save"
          >
            <template #icon><Save class="mr-1.5 size-4" /></template>
          </Button>
        </div>
      </div>

      <Textarea v-model="draft" class="w-full font-mono text-[12.5px] leading-relaxed" rows="26" />

      <p class="mt-2 text-[12px] leading-relaxed text-slate-500">
        Переменные в двойных фигурных скобках подставляются перед отправкой. Незаполненные
        заменяются прочерком, литерал в промпт не попадает.
      </p>
    </section>
  </div>
</template>
