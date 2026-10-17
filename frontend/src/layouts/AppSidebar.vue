<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import {
  Activity,
  Bot,
  Building2,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Gauge,
  Globe,
  Inbox,
  LayoutDashboard,
  Map,
  ListChecks,
  Mail,
  Search,
  Send,
  ShieldAlert,
  Sliders,
  Sparkles,
  UserRound
} from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const route = useRoute()

const groups = [
  {
    title: null,
    items: [
      { to: '/welcome', label: 'С чего начать', icon: Map },
      { to: '/dashboard', label: 'Дашборд', icon: LayoutDashboard }
    ]
  },
  {
    title: 'Бот',
    items: [
      { to: '/vacancies', label: 'Вакансии', icon: Inbox },
      { to: '/review', label: 'Очередь проверки', icon: ListChecks },
      { to: '/suspicious', label: 'Подозрительные', icon: ShieldAlert },
      { to: '/applications', label: 'Отклики', icon: Send },
      { to: '/activity', label: 'Активность', icon: Activity }
    ]
  },
  {
    title: 'Поиск',
    items: [
      { to: '/search-profiles', label: 'Поисковые профили', icon: Search },
      { to: '/companies', label: 'Компании', icon: Building2 }
    ]
  },
  {
    title: 'Резюме',
    items: [
      { to: '/resumes', label: 'Мои резюме', icon: FileText },
      { to: '/letter-examples', label: 'Примеры писем', icon: Mail }
    ]
  },
  {
    title: 'Настройки',
    items: [
      { to: '/settings/providers', label: 'Модели и провайдеры', icon: Sparkles },
      { to: '/settings/prompts', label: 'Промпты', icon: UserRound },
      { to: '/settings/delays', label: 'Задержки и лимиты', icon: Gauge },
      { to: '/settings/browser', label: 'Браузер', icon: Globe },
      { to: '/settings/general', label: 'Общие', icon: Sliders }
    ]
  }
]

function isActive(to: string): boolean {
  return route.path === to || route.path.startsWith(to + '/')
}
</script>

<template>
  <aside
    data-tour="navigation"
    class="flex h-full shrink-0 flex-col overflow-hidden border-r border-slate-200 bg-slate-50 transition-[width] duration-150"
    :class="ui.sidebarCollapsed ? 'w-16' : 'w-60'"
  >
    <div
      class="flex h-14 shrink-0 items-center gap-2"
      :class="ui.sidebarCollapsed ? 'justify-center' : 'px-4'"
    >
      <Bot class="size-5 shrink-0 text-teal-700" />
      <span
        v-if="!ui.sidebarCollapsed"
        class="text-[15px] font-semibold tracking-tight text-slate-800"
      >
        HH JobPilot
      </span>
    </div>

    <nav
      class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2 pb-3"
      aria-label="Основное меню"
    >
      <div
        v-for="(group, index) in groups"
        :key="index"
        :class="
          ui.sidebarCollapsed
            ? 'mb-2 border-t border-slate-200 pt-2 first:border-0 first:pt-0'
            : 'mb-4'
        "
      >
        <p
          v-if="group.title && !ui.sidebarCollapsed"
          class="px-3 pb-1.5 text-[11px] font-semibold tracking-[0.08em] text-slate-400 uppercase"
        >
          {{ group.title }}
        </p>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          v-tooltip.right="ui.sidebarCollapsed ? item.label : undefined"
          :to="item.to"
          :aria-label="ui.sidebarCollapsed ? item.label : undefined"
          :data-tour="
            item.to === '/resumes'
              ? 'resumes'
              : item.to === '/search-profiles'
                ? 'search'
                : item.to === '/settings/providers'
                  ? 'providers'
                  : item.to === '/settings/browser'
                    ? 'browser'
                    : undefined
          "
          class="mb-0.5 flex min-h-9 items-center rounded-[10px] text-[13.5px] no-underline transition-colors"
          :class="[
            ui.sidebarCollapsed ? 'justify-center px-0' : 'gap-2.5 px-3',
            isActive(item.to)
              ? 'bg-teal-700/10 font-medium text-teal-900'
              : 'text-slate-600 hover:bg-slate-200/60'
          ]"
        >
          <component :is="item.icon" class="size-[17px] shrink-0" />
          <span v-if="!ui.sidebarCollapsed" class="truncate">{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>

    <button
      type="button"
      :aria-label="ui.sidebarCollapsed ? 'Развернуть меню' : 'Свернуть меню'"
      :title="ui.sidebarCollapsed ? 'Развернуть меню' : 'Свернуть меню'"
      class="flex min-h-11 shrink-0 items-center gap-2.5 border-t border-slate-200 text-[13px] text-slate-500 hover:bg-slate-200/60"
      :class="ui.sidebarCollapsed ? 'justify-center px-0' : 'px-4'"
      @click="ui.sidebarCollapsed = !ui.sidebarCollapsed"
    >
      <component :is="ui.sidebarCollapsed ? ChevronsRight : ChevronsLeft" class="size-4 shrink-0" />
      <span v-if="!ui.sidebarCollapsed">Свернуть</span>
    </button>
  </aside>
</template>
