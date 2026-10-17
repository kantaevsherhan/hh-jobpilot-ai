import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { router } from '@/router'

/** Отдельный роутер на тест: общий хранит историю между проверками. */
const makeRouter = () =>
  createRouter({ history: createMemoryHistory(), routes: router.getRoutes() })

/** Пункты бокового меню из §27 — у каждого должен быть рабочий экран. */
const MENU = [
  '/dashboard',
  '/vacancies',
  '/review',
  '/suspicious',
  '/applications',
  '/activity',
  '/search-profiles',
  '/companies',
  '/resumes',
  '/letter-examples',
  '/settings/providers',
  '/settings/prompts',
  '/settings/delays',
  '/settings/browser',
  '/settings/general',
  '/settings/backups'
]

describe('маршруты', () => {
  it.each(MENU)('%s ведёт на существующий экран', (path) => {
    const matched = router.resolve(path).matched

    expect(matched.length).toBeGreaterThan(0)
    expect(matched[0].components?.default).toBeDefined()
  })

  it.each(MENU)(
    '%s загружается без ошибок импорта',
    async (path) => {
      const component = router.resolve(path).matched[0].components?.default

      // Все экраны подгружаются лениво: битый импорт иначе всплыл бы только у пользователя
      expect(typeof component).toBe('function')
      await expect((component as () => Promise<unknown>)()).resolves.toBeTruthy()
    },
    20000
  )

  // resolve() редиректы не выполняет — они срабатывают при навигации
  it('корень уводит на дашборд', async () => {
    const isolated = makeRouter()
    await isolated.push('/')

    expect(isolated.currentRoute.value.path).toBe('/dashboard')
  })

  it('несуществующий адрес не показывает пустой экран', async () => {
    const isolated = makeRouter()
    await isolated.push('/такого-нет')

    expect(isolated.currentRoute.value.path).toBe('/dashboard')
  })

  it('карточка вакансии открывается по номеру', () => {
    const resolved = router.resolve('/vacancies/42')

    expect(resolved.name).toBe('vacancy')
    expect(resolved.params.id).toBe('42')
  })

  it('заголовок вкладки берётся из маршрута', async () => {
    const isolated = makeRouter()
    await isolated.push('/review')

    expect(isolated.currentRoute.value.meta.title).toBe('Очередь проверки')
  })
})
