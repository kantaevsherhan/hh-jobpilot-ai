<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { CircleCheck, CircleSlash, LogIn, Loader2, TriangleAlert } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { useToast } from 'primevue/usetoast'
import {
  useBrowserStatus,
  useCheckAuth,
  useCloseBrowser,
  useRestartBrowser,
  useStartBrowser
} from '@/queries/browser'

const toast = useToast()
const { data: status } = useBrowserStatus()
const start = useStartBrowser()
const check = useCheckAuth()
const restart = useRestartBrowser()
const close = useCloseBrowser()

const state = computed(() => status.value?.state ?? 'STOPPED')

const view = computed(() => {
  switch (state.value) {
    case 'READY':
      return { icon: CircleCheck, tone: 'text-teal-700', bg: 'bg-teal-50' }
    case 'NEEDS_LOGIN':
      return { icon: LogIn, tone: 'text-amber-700', bg: 'bg-amber-50' }
    case 'ERROR':
      return { icon: TriangleAlert, tone: 'text-red-700', bg: 'bg-red-50' }
    case 'STARTING':
      return { icon: Loader2, tone: 'text-slate-600', bg: 'bg-slate-100' }
    default:
      return { icon: CircleSlash, tone: 'text-slate-500', bg: 'bg-slate-100' }
  }
})

const busy = computed(
  () =>
    start.isPending.value ||
    check.isPending.value ||
    restart.isPending.value ||
    close.isPending.value
)

function onError(error: unknown) {
  toast.add({ severity: 'error', summary: 'Браузер', detail: toMessage(error), life: 8000 })
}
</script>

<template>
  <div class="max-w-2xl">
    <div class="rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="flex items-start gap-3">
        <span class="flex size-9 items-center justify-center rounded-[10px]" :class="view.bg">
          <component :is="view.icon" class="size-5" :class="view.tone" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-[14px] font-medium text-slate-900">{{ status?.label ?? 'Не запущен' }}</p>
          <p class="mt-0.5 font-mono text-[12px] break-all text-slate-500">
            {{ status?.user_data_dir }}
          </p>
        </div>
      </div>

      <p class="mt-4 max-w-prose text-[13px] leading-relaxed text-slate-600">
        Chromium запускается видимым и с постоянным профилем: cookies остаются на диске, поэтому
        вход в HH переживает перезапуск приложения. Скрытый режим для откликов запрещён — вы должны
        видеть, что происходит, и иметь возможность вмешаться.
      </p>

      <div class="mt-4 flex flex-wrap gap-2">
        <Button
          v-if="!status?.is_running"
          size="small"
          label="Запустить браузер"
          :loading="start.isPending.value"
          @click="start.mutate(undefined, { onError })"
        />
        <template v-else>
          <Button
            size="small"
            label="Проверить вход"
            :loading="check.isPending.value"
            @click="check.mutate(undefined, { onError })"
          />
          <Button
            size="small"
            severity="secondary"
            outlined
            label="Перезапустить"
            :loading="restart.isPending.value"
            @click="restart.mutate(undefined, { onError })"
          />
          <Button
            size="small"
            severity="secondary"
            outlined
            label="Закрыть"
            :loading="close.isPending.value"
            @click="close.mutate(undefined, { onError })"
          />
        </template>
      </div>

      <Message v-if="state === 'NEEDS_LOGIN'" severity="warn" size="small" class="mt-4">
        Войдите в HH в открывшемся окне вручную, затем нажмите «Проверить вход». Капчу и SMS бот не
        обходит и не проходит за вас.
      </Message>

      <Message
        v-if="state === 'ERROR' && status?.last_error"
        severity="error"
        size="small"
        class="mt-4"
      >
        {{ status.last_error }}
      </Message>

      <p v-if="busy" class="mt-3 text-[12.5px] text-slate-500">Выполняется…</p>
    </div>
  </div>
</template>
