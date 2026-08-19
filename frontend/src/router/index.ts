import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const StubPage = () => import('@/pages/StubPage.vue')

/** Экран будущей фазы: показывает заглушку с её номером, а не пустую страницу. */
function stub(path: string, name: string, title: string, phase: string): RouteRecordRaw {
  return { path, name, meta: { title }, component: StubPage, props: { title, phase } }
}

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    name: 'dashboard',
    meta: { title: 'Дашборд' },
    component: () => import('@/pages/DashboardPage.vue')
  },
  {
    path: '/resumes',
    name: 'resumes',
    meta: { title: 'Мои резюме' },
    component: () => import('@/pages/ResumesPage.vue')
  },
  {
    path: '/resumes/:id',
    name: 'resume',
    meta: { title: 'Резюме' },
    component: () => import('@/pages/ResumePage.vue')
  },
  stub('/vacancies', 'vacancies', 'Вакансии', '4'),
  stub('/review', 'review', 'Очередь проверки', '10'),
  stub('/suspicious', 'suspicious', 'Подозрительные', '6'),
  stub('/applications', 'applications', 'Отклики', '8'),
  stub('/activity', 'activity', 'Активность', '9'),
  stub('/search-profiles', 'search-profiles', 'Поисковые профили', '4'),
  stub('/companies', 'companies', 'Правила по компаниям', '5'),
  stub('/letter-examples', 'letter-examples', 'Примеры писем', '7'),
  stub('/settings/providers', 'providers', 'Модели и провайдеры', '2'),
  stub('/settings/prompts', 'prompts', 'Промпты', '2'),
  stub('/settings/delays', 'delays', 'Задержки и лимиты', '9'),
  stub('/settings/browser', 'browser', 'Браузер', '3'),
  stub('/settings/general', 'general', 'Общие настройки', '11'),
  stub('/settings/backups', 'backups', 'Резервные копии', '11'),
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

export const router = createRouter({ history: createWebHistory(), routes })

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title ? `${title} · HH JobPilot` : 'HH JobPilot'
})
