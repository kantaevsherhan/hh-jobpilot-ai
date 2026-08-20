import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

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
  {
    path: '/vacancies/:id',
    name: 'vacancy',
    meta: { title: 'Вакансия' },
    component: () => import('@/pages/VacancyPage.vue')
  },
  {
    path: '/vacancies',
    name: 'vacancies',
    meta: { title: 'Вакансии' },
    component: () => import('@/pages/VacanciesPage.vue')
  },
  {
    path: '/review',
    name: 'review',
    meta: { title: 'Очередь проверки' },
    component: () => import('@/pages/ReviewQueuePage.vue')
  },
  {
    path: '/suspicious',
    name: 'suspicious',
    meta: { title: 'Подозрительные' },
    component: () => import('@/pages/SuspiciousPage.vue')
  },
  {
    path: '/applications',
    name: 'applications',
    meta: { title: 'Отклики' },
    component: () => import('@/pages/ApplicationsPage.vue')
  },
  {
    path: '/activity',
    name: 'activity',
    meta: { title: 'Активность' },
    component: () => import('@/pages/ActivityPage.vue')
  },
  {
    path: '/search-profiles',
    name: 'search-profiles',
    meta: { title: 'Поисковые профили' },
    component: () => import('@/pages/SearchProfilesPage.vue')
  },
  {
    path: '/companies',
    name: 'companies',
    meta: { title: 'Правила по компаниям' },
    component: () => import('@/pages/CompaniesPage.vue')
  },
  {
    path: '/letter-examples',
    name: 'letter-examples',
    meta: { title: 'Примеры писем' },
    component: () => import('@/pages/LetterExamplesPage.vue')
  },
  {
    path: '/settings/providers',
    name: 'providers',
    meta: { title: 'Модели и провайдеры' },
    component: () => import('@/pages/ProvidersPage.vue')
  },
  {
    path: '/settings/prompts',
    name: 'prompts',
    meta: { title: 'Промпты' },
    component: () => import('@/pages/PromptsPage.vue')
  },
  {
    path: '/settings/delays',
    name: 'delays',
    meta: { title: 'Задержки и лимиты' },
    component: () => import('@/pages/DelaysPage.vue')
  },
  {
    path: '/settings/browser',
    name: 'browser',
    meta: { title: 'Браузер' },
    component: () => import('@/pages/BrowserPage.vue')
  },
  {
    path: '/settings/general',
    name: 'general',
    meta: { title: 'Общие настройки' },
    component: () => import('@/pages/GeneralPage.vue')
  },
  {
    path: '/settings/backups',
    name: 'backups',
    meta: { title: 'Резервные копии' },
    component: () => import('@/pages/BackupsPage.vue')
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

export const router = createRouter({ history: createWebHistory(), routes })

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title ? `${title} · HH JobPilot` : 'HH JobPilot'
})
