<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { Check, LogIn } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { useBrowserStatus, useCheckAuth, useStartBrowser } from '@/queries/browser'
import { useProviders } from '@/queries/llm'
import { useResumes } from '@/queries/resumes'
import { useSearchProfiles } from '@/queries'
import { useUiStore } from '@/stores/ui'

const toast = useToast()
const ui = useUiStore()

const { data: resumes } = useResumes()
const { data: providers } = useProviders()
const { data: browserStatus } = useBrowserStatus()
const { data: profiles } = useSearchProfiles(() => ui.resumeId)

const start = useStartBrowser()
const check = useCheckAuth()

const loggedIn = computed(() => browserStatus.value?.state === 'READY')
const browserRunning = computed(() => browserStatus.value?.is_running === true)

const steps = computed(() => [
  {
    key: 'login',
    title: 'Войти в hh.kz',
    hint: 'Откроется обычное окно Chromium — войдите в свой аккаунт руками. Бот ничего не регистрирует и не подбирает пароли, дальше он работает от вашего аккаунта. Сессия сохранится и переживёт перезапуск.',
    done: loggedIn.value
  },
  {
    key: 'resume',
    title: 'Добавить резюме',
    hint: 'Вставьте текст резюме с hh.kz — из него собирается выжимка и пишутся письма.',
    done: (resumes.value?.length ?? 0) > 0,
    to: '/resumes'
  },
  {
    key: 'provider',
    title: 'Настроить модели',
    hint: 'Локальная Ollama заводится сама. Проверьте её кнопкой «Проверить» и задайте маршруты по шагам.',
    done: (providers.value ?? []).some((provider) => provider.is_enabled),
    to: '/settings/providers'
  },
  {
    key: 'profile',
    title: 'Создать поисковый профиль',
    hint: 'Запросы, регионы, минимальная зарплата и стоп-слова. Без профиля прогон не запустится.',
    done: (profiles.value?.length ?? 0) > 0,
    to: '/search-profiles'
  }
])

const allDone = computed(() => steps.value.every((step) => step.done))

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Браузер', detail: toMessage(error), life: 8000 })
}

function openBrowser() {
  start.mutate(undefined, {
    onSuccess: () => {
      toast.add({
        severity: 'info',
        summary: 'Браузер открыт',
        detail: 'Войдите в hh.kz в открывшемся окне, затем нажмите «Я вошёл».',
        life: 10000
      })
    },
    onError: fail
  })
}
</script>

<template>
  <section v-if="!allDone" class="rounded-[14px] border border-slate-200 bg-white p-5">
    <h2 class="text-[15px] font-semibold tracking-tight text-slate-900">Что нужно сделать</h2>
    <p class="mt-1 max-w-prose text-[13px] leading-relaxed text-slate-600">
      Четыре шага, после которых можно запускать прогон.
    </p>

    <ol class="mt-4 space-y-3">
      <li v-for="(step, position) in steps" :key="step.key" class="flex items-start gap-3">
        <span
          class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
          :class="
            step.done ? 'bg-teal-700 text-white' : 'border border-slate-300 bg-white text-slate-500'
          "
        >
          <Check v-if="step.done" class="size-3" />
          <template v-else>{{ position + 1 }}</template>
        </span>

        <div class="min-w-0 flex-1">
          <p
            class="text-[13.5px] font-medium"
            :class="step.done ? 'text-slate-400 line-through' : 'text-slate-800'"
          >
            {{ step.title }}
          </p>
          <p
            v-if="!step.done"
            class="mt-0.5 max-w-prose text-[12.5px] leading-relaxed text-slate-500"
          >
            {{ step.hint }}
          </p>
        </div>

        <div v-if="!step.done" class="shrink-0">
          <template v-if="step.key === 'login'">
            <Button
              v-if="!browserRunning"
              size="small"
              label="Открыть браузер"
              :loading="start.isPending.value"
              @click="openBrowser"
            >
              <template #icon><LogIn class="mr-1.5 size-3.5" /></template>
            </Button>
            <Button
              v-else
              size="small"
              severity="secondary"
              outlined
              label="Я вошёл"
              :loading="check.isPending.value"
              @click="check.mutate(undefined, { onError: fail })"
            />
          </template>
          <RouterLink v-else-if="step.to" :to="step.to">
            <Button size="small" severity="secondary" outlined label="Открыть" />
          </RouterLink>
        </div>
      </li>
    </ol>
  </section>
</template>
