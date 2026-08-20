import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { applyToVacancy, fetchVacancies, generateLetter } from '@/api/vacancies'

const VACANCY_PAGE = { items: [], total: 0 }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('запросы к собственному API', () => {
  it('фильтры уходят параметрами запроса, а не собираются в строку руками', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: VACANCY_PAGE })

    await fetchVacancies({
      resume_id: 1,
      status: ['REVIEW_REQUIRED', 'RECOMMENDED'],
      min_score: 75,
      page: 2
    })

    expect(get).toHaveBeenCalledWith('/vacancies', {
      params: {
        resume_id: 1,
        status: ['REVIEW_REQUIRED', 'RECOMMENDED'],
        min_score: 75,
        page: 2
      }
    })
  })

  it('генерация письма ждёт дольше обычного запроса', async () => {
    // Локальная модель пишет письмо минуты, дефолтные 30 секунд её обрывают
    const post = vi.spyOn(api, 'post').mockResolvedValue({
      data: {
        id: 1,
        version: 1,
        source: 'AI',
        language: 'ru',
        content: 'Здравствуйте',
        char_count: 11,
        fact_check_json: null,
        fact_check_passed: null,
        is_selected: true,
        created_at: '2026-08-20T10:00:00'
      }
    })

    await generateLetter(7, { resume_id: 1 })

    const [, , options] = post.mock.calls[0]
    expect((options as { timeout: number }).timeout).toBeGreaterThan(60_000)
  })

  it('режим отправки передаётся явно и не подставляется по умолчанию', async () => {
    const post = vi
      .spyOn(api, 'post')
      .mockResolvedValue({ data: { status: 'APPLY_PREPARED', message: 'ок' } })

    await applyToVacancy(7, { resume_id: 1, letter_id: 3, runtime_mode: 'DRY_RUN' })

    const [, payload] = post.mock.calls[0]
    expect(payload).toEqual({ resume_id: 1, letter_id: 3, runtime_mode: 'DRY_RUN' })
  })

  it('ответ, не подходящий под схему, роняет запрос, а не едет дальше в интерфейс', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { items: [{ id: 'не число' }], total: 1 } })

    await expect(fetchVacancies({ resume_id: 1 })).rejects.toThrow()
  })
})
