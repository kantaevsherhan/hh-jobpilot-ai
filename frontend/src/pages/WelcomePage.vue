<script setup lang="ts">
import { computed, nextTick, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { driver } from 'driver.js'
import {
  ArrowRight,
  BookOpen,
  Check,
  CircleHelp,
  ExternalLink,
  LogIn,
  Play,
  Sparkles
} from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { useBrowserStatus, useCheckAuth, useStartBrowser } from '@/queries/browser'
import { useProviders } from '@/queries/llm'
import { useResumes } from '@/queries/resumes'
import { useRuns, useSearchProfiles } from '@/queries'
import { useUiStore } from '@/stores/ui'
import 'driver.js/dist/driver.css'

const ui = useUiStore()
const toast = useToast()
const { data: resumes } = useResumes()
const { data: providers } = useProviders()
const { data: browser } = useBrowserStatus()
const { data: profiles } = useSearchProfiles(() => ui.resumeId)
const { data: runs } = useRuns(() => ui.resumeId)
const startBrowser = useStartBrowser()
const checkAuth = useCheckAuth()

onMounted(() => {
  try {
    localStorage.setItem('jobpilot.welcomeSeen', '1')
  } catch {
    // Руководство доступно и без локального хранилища.
  }
})

const selectedResume = computed(() => resumes.value?.find((item) => item.id === ui.resumeId))
const resumeReady = computed(() => Boolean(selectedResume.value?.raw_text.trim()))
const providerConfigured = computed(() => (providers.value ?? []).some((item) => item.is_enabled))
const browserReady = computed(() => browser.value?.state === 'READY')
const profileReady = computed(() =>
  (profiles.value ?? []).some((item) => item.enabled && item.queries.length > 0)
)
const dryRunDone = computed(() =>
  (runs.value ?? []).some((item) => item.runtime_mode === 'DRY_RUN')
)

const steps = computed(() => [
  {
    title: 'Добавьте резюме',
    description:
      'Создайте резюме и вставьте его текст с hh.kz. Добавьте только проверенные факты: на них бот опирается при написании писем.',
    done: resumeReady.value,
    doneLabel: 'Текст добавлен',
    to: ui.resumeId ? `/resumes/${String(ui.resumeId)}` : '/resumes',
    action: 'Открыть резюме'
  },
  {
    title: 'Подключите модель',
    description:
      'Откройте «Модели и провайдеры», нажмите «Проверить» у выбранной модели и настройте маршруты. Включённая запись ещё не означает, что модель отвечает.',
    done: providerConfigured.value,
    doneLabel: 'Провайдер добавлен · проверьте соединение',
    to: '/settings/providers',
    action: 'Открыть модели'
  },
  {
    title: 'Войдите в hh.kz',
    description:
      'Запустите отдельное окно Chromium, войдите в свой аккаунт вручную, затем нажмите «Проверить вход». Пароль остаётся в браузере.',
    done: browserReady.value,
    doneLabel: 'Вход подтверждён',
    to: '/settings/browser',
    action: 'Настройки браузера'
  },
  {
    title: 'Создайте поисковый профиль',
    description:
      'Укажите запросы, регионы и фильтры для выбранного резюме. Без включённого профиля искать вакансии нечем.',
    done: profileReady.value,
    doneLabel: 'Профиль включён',
    to: ui.resumeId ? '/search-profiles' : '/resumes',
    action: ui.resumeId ? 'Настроить поиск' : 'Сначала выберите резюме'
  },
  {
    title: 'Сделайте пробный прогон',
    description:
      'Оставьте в шапке ручной и пробный режимы. Бот найдёт и разберёт вакансии, но не отправит отклики работодателям.',
    done: dryRunDone.value,
    doneLabel: 'Пробный прогон был',
    to: '/dashboard',
    action: 'Перейти к запуску'
  }
])

const completed = computed(() => steps.value.filter((item) => item.done).length)

function onBrowserError(error: unknown) {
  toast.add({ severity: 'error', summary: 'Браузер', detail: toMessage(error), life: 8000 })
}

function openBrowser() {
  startBrowser.mutate(undefined, {
    onSuccess: () => {
      toast.add({
        severity: 'info',
        summary: 'Окно hh.kz открыто',
        detail: 'Войдите вручную, вернитесь сюда и нажмите «Проверить вход».',
        life: 9000
      })
    },
    onError: onBrowserError
  })
}

async function showTour() {
  ui.sidebarCollapsed = false
  await nextTick()
  driver({
    showProgress: true,
    progressText: '{{current}} / {{total}}',
    nextBtnText: 'Далее',
    prevBtnText: 'Назад',
    doneBtnText: 'Понятно',
    closeBtnLabel: 'Закрыть обзор',
    overlayColor: '#0f172a',
    overlayOpacity: 0.58,
    stageRadius: 12,
    smoothScroll: true,
    disableActiveInteraction: true,
    skipMissingElement: true,
    popoverClass: 'jobpilot-tour',
    steps: [
      {
        element: '[data-tour="welcome"]',
        popover: {
          title: 'С чего начать',
          description: 'Эта страница показывает порядок настройки и ведёт к нужным действиям.'
        }
      },
      {
        element: '[data-tour="resumes"]',
        popover: {
          title: 'Резюме',
          description: 'Здесь хранится текст резюме и факты, которые можно использовать в письмах.',
          side: 'right'
        }
      },
      {
        element: '[data-tour="providers"]',
        popover: {
          title: 'Модели',
          description:
            'Здесь проверяют подключение Ollama или внешнего провайдера и назначают модель каждому шагу.',
          side: 'right'
        }
      },
      {
        element: '[data-tour="browser"]',
        popover: {
          title: 'Вход в hh.kz',
          description:
            'Запустите браузер, войдите лично и проверьте сессию. Приложение не вводит пароль за вас.',
          side: 'right'
        }
      },
      {
        element: '[data-tour="search"]',
        popover: {
          title: 'Условия поиска',
          description: 'Поисковый профиль задаёт запросы, регионы, фильтры и лимит вакансий.',
          side: 'right'
        }
      },
      {
        element: '[data-tour="resume-picker"]',
        popover: {
          title: 'Выбранное резюме',
          description: 'Профили, вакансии и статистика относятся к резюме, выбранному в шапке.',
          side: 'bottom'
        }
      },
      {
        element: '[data-tour="bot-mode"]',
        popover: {
          title: 'Степень автоматизации',
          description:
            'Начните с ручного режима: решения и письма можно проверить перед действием.',
          side: 'bottom'
        }
      },
      {
        element: '[data-tour="runtime-mode"]',
        popover: {
          title: 'Пробный режим и реальная отправка',
          description:
            'В пробном режиме бот не отправляет отклики. Реальную отправку включайте после проверки результатов.',
          side: 'bottom'
        }
      },
      {
        element: '[data-tour="launch"]',
        popover: {
          title: 'Запуск',
          description:
            'После настройки резюме, модели, входа и поиска начните первый пробный прогон здесь.',
          side: 'bottom'
        }
      }
    ]
  }).drive()
}

const sections = [
  {
    title: 'Работа с вакансиями',
    pages: [
      {
        to: '/dashboard',
        name: 'Дашборд',
        description: 'Счётчики и результаты последнего прогона.'
      },
      {
        to: '/vacancies',
        name: 'Вакансии',
        description: 'Найденные вакансии и решения по каждой.'
      },
      {
        to: '/review',
        name: 'Очередь проверки',
        description: 'Решения и письма, ожидающие вашего подтверждения.'
      },
      {
        to: '/suspicious',
        name: 'Подозрительные',
        description: 'Вакансии, где нужна дополнительная осторожность.'
      },
      {
        to: '/applications',
        name: 'Отклики',
        description: 'История подготовленных и отправленных откликов.'
      },
      { to: '/activity', name: 'Активность', description: 'Прогоны, события и причины ошибок.' }
    ]
  },
  {
    title: 'Подготовка поиска',
    pages: [
      {
        to: '/resumes',
        name: 'Мои резюме',
        description: 'Текст резюме, навыки, факты и выжимка для модели.'
      },
      {
        to: '/search-profiles',
        name: 'Поисковые профили',
        description: 'Запросы, регионы, зарплата и фильтры.'
      },
      { to: '/companies', name: 'Компании', description: 'Правила для конкретных работодателей.' },
      {
        to: '/letter-examples',
        name: 'Примеры писем',
        description: 'Образцы тона и содержания сопроводительных писем.'
      }
    ]
  },
  {
    title: 'Настройки',
    pages: [
      {
        to: '/settings/providers',
        name: 'Модели и провайдеры',
        description: 'Подключение, проверка и маршруты моделей.'
      },
      {
        to: '/settings/browser',
        name: 'Браузер',
        description: 'Вход на hh.kz и состояние сессии.'
      },
      {
        to: '/settings/prompts',
        name: 'Промпты',
        description: 'Инструкции, которые получает модель.'
      },
      {
        to: '/settings/delays',
        name: 'Задержки и лимиты',
        description: 'Темп работы и ограничения откликов.'
      },
      { to: '/settings/general', name: 'Общие', description: 'Общие параметры работы приложения.' },
      {
        to: '/settings/backups',
        name: 'Резервные копии',
        description: 'Сохранение и выгрузка локальных данных.'
      }
    ]
  }
]
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-6 pb-12">
    <section
      data-tour="welcome"
      class="relative overflow-hidden rounded-[20px] border border-teal-200 bg-gradient-to-br from-teal-950 via-teal-900 to-slate-900 p-6 text-white sm:p-8"
    >
      <div class="relative z-10 max-w-2xl">
        <div
          class="mb-4 flex items-center gap-2 text-[12px] font-semibold tracking-wide text-teal-200 uppercase"
        >
          <Sparkles class="size-4" /> Первый запуск
        </div>
        <h2 class="text-2xl font-semibold tracking-tight sm:text-3xl">
          Начните с пяти простых шагов
        </h2>
        <p class="mt-3 max-w-xl text-[14px] leading-relaxed text-teal-50/85">
          Подготовьте резюме, модель, вход в hh.kz и поиск. Затем запустите пробный прогон без
          отправки откликов.
        </p>
        <div class="mt-6 flex flex-wrap items-center gap-3">
          <Button size="small" label="Показать интерфейс" @click="showTour">
            <template #icon><BookOpen class="mr-1.5 size-4" /></template>
          </Button>
          <RouterLink
            to="/dashboard"
            class="text-[13px] font-medium text-white underline underline-offset-4"
          >
            Перейти к дашборду
          </RouterLink>
        </div>
      </div>
      <div
        class="pointer-events-none absolute -top-28 -right-16 size-72 rounded-full border border-white/15 bg-teal-400/10"
      />
    </section>

    <section class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_270px]">
      <div class="rounded-[16px] border border-slate-200 bg-white p-5 sm:p-6">
        <div class="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 class="text-[17px] font-semibold text-slate-900">Ваш план настройки</h3>
            <p class="mt-1 text-[13px] text-slate-500">Статусы обновляются по данным приложения.</p>
          </div>
          <span class="rounded-full bg-teal-50 px-3 py-1 text-[12px] font-semibold text-teal-800">
            {{ completed }} из 5
          </span>
        </div>

        <ol class="space-y-2">
          <li
            v-for="(step, index) in steps"
            :key="step.title"
            class="rounded-[12px] border p-4"
            :class="step.done ? 'border-teal-100 bg-teal-50/40' : 'border-slate-200 bg-white'"
          >
            <div class="flex flex-wrap items-start gap-3">
              <span
                class="flex size-7 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold"
                :class="step.done ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-600'"
              >
                <Check v-if="step.done" class="size-4" />
                <template v-else>{{ index + 1 }}</template>
              </span>
              <div class="min-w-0 flex-1">
                <h4 class="text-[14px] font-semibold text-slate-900">{{ step.title }}</h4>
                <p class="mt-1 max-w-2xl text-[12.5px] leading-relaxed text-slate-600">
                  {{ step.description }}
                </p>
                <p v-if="step.done" class="mt-2 text-[12px] font-medium text-teal-700">
                  {{ step.doneLabel }}
                </p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <RouterLink
                    :to="step.to"
                    class="inline-flex items-center gap-1 text-[12.5px] font-medium text-teal-800 hover:underline"
                  >
                    {{ step.action }} <ArrowRight class="size-3.5" />
                  </RouterLink>
                  <template v-if="index === 2 && !browserReady">
                    <button
                      v-if="!browser?.is_running"
                      type="button"
                      class="text-[12.5px] font-medium text-slate-700 hover:underline disabled:opacity-50"
                      :disabled="startBrowser.isPending.value"
                      @click="openBrowser"
                    >
                      Открыть окно hh.kz
                    </button>
                    <button
                      v-else
                      type="button"
                      class="text-[12.5px] font-medium text-slate-700 hover:underline disabled:opacity-50"
                      :disabled="checkAuth.isPending.value"
                      @click="checkAuth.mutate(undefined, { onError: onBrowserError })"
                    >
                      Проверить вход
                    </button>
                  </template>
                </div>
              </div>
            </div>
          </li>
        </ol>
      </div>

      <aside class="space-y-4">
        <div class="rounded-[16px] border border-amber-200 bg-amber-50 p-5">
          <div class="flex items-center gap-2 text-[13px] font-semibold text-amber-900">
            <CircleHelp class="size-4" /> Безопасный первый прогон
          </div>
          <p class="mt-2 text-[12.5px] leading-relaxed text-amber-950/80">
            Выберите «Ручной» и оставьте «Пробный режим» в шапке. Так можно посмотреть найденные
            вакансии и письма до настоящей отправки.
          </p>
        </div>
        <div class="rounded-[16px] border border-slate-200 bg-white p-5">
          <div class="flex items-center gap-2 text-[13px] font-semibold text-slate-900">
            <LogIn class="size-4 text-teal-700" /> Как работает вход
          </div>
          <p class="mt-2 text-[12.5px] leading-relaxed text-slate-600">
            Входите на hh.kz только в открывшемся окне Chromium. После входа вернитесь в приложение
            и проверьте сессию.
          </p>
          <RouterLink
            to="/settings/browser"
            class="mt-3 inline-flex items-center gap-1 text-[12.5px] font-medium text-teal-800 hover:underline"
          >
            Открыть браузер <ExternalLink class="size-3.5" />
          </RouterLink>
        </div>
      </aside>
    </section>

    <section>
      <div class="mb-4 flex items-center gap-2">
        <BookOpen class="size-5 text-teal-700" />
        <div>
          <h3 class="text-[17px] font-semibold text-slate-900">Что где находится</h3>
          <p class="text-[12.5px] text-slate-500">
            Короткая карта страниц. К каждой можно перейти прямо отсюда.
          </p>
        </div>
      </div>
      <div class="grid gap-4 lg:grid-cols-3">
        <div
          v-for="section in sections"
          :key="section.title"
          class="rounded-[16px] border border-slate-200 bg-white p-5"
        >
          <h4 class="mb-3 text-[14px] font-semibold text-slate-900">{{ section.title }}</h4>
          <div class="space-y-1">
            <RouterLink
              v-for="page in section.pages"
              :key="page.to"
              :to="page.to"
              class="group block rounded-[9px] px-2 py-2 no-underline hover:bg-slate-50"
            >
              <span
                class="flex items-center justify-between gap-2 text-[13px] font-medium text-slate-800 group-hover:text-teal-800"
              >
                {{ page.name }} <ArrowRight class="size-3.5 shrink-0 text-slate-400" />
              </span>
              <span class="mt-0.5 block text-[12px] leading-snug text-slate-500">{{
                page.description
              }}</span>
            </RouterLink>
          </div>
        </div>
      </div>
    </section>

    <RouterLink
      to="/dashboard"
      class="inline-flex items-center gap-2 text-[13px] font-medium text-teal-800 hover:underline"
    >
      <Play class="size-4" /> Перейти к дашборду
    </RouterLink>
  </div>
</template>
