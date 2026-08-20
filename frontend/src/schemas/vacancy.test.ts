import { describe, expect, it } from 'vitest'
import { analysisSchema, vacancyPageSchema, vacancyRowSchema } from '@/schemas/vacancy'
import { resumeSchema } from '@/schemas/resume'
import { providerSchema } from '@/schemas/llm'

/** Ответ бэкенда как он приходит на самом деле. */
const VACANCY = {
  id: 1,
  hh_id: '136308784',
  url: 'https://hh.kz/vacancy/136308784',
  title: 'Senior Backend-разработчик (Node.js / NestJS)',
  company_name: 'ООО Топассистент',
  salary_from: 5000,
  salary_to: null,
  currency: 'EUR',
  salary_gross: false,
  work_format: 'REMOTE',
  experience: 'более 6 лет',
  area: null,
  published_at: null,
  first_seen_at: '2026-08-20T09:20:24',
  is_closed: false,
  status: 'RECOMMENDED',
  skip_reason: null,
  skip_details: null,
  score: 95,
  is_suspicious: false,
  hidden_instructions: [],
  decision_id: 3,
  applied_at: null
}

describe('схемы ответов API', () => {
  it('разбирает вакансию из настоящего ответа', () => {
    const parsed = vacancyRowSchema.parse(VACANCY)

    expect(parsed.score).toBe(95)
    expect(parsed.company_name).toBe('ООО Топассистент')
  })

  it('страница вакансий содержит счётчик для серверной пагинации', () => {
    const page = vacancyPageSchema.parse({ items: [VACANCY], total: 42 })

    expect(page.total).toBe(42)
    expect(page.items).toHaveLength(1)
  })

  it('отсутствующее поле — это ошибка, а не тихий undefined', () => {
    const { score: _score, ...broken } = VACANCY

    expect(() => vacancyRowSchema.parse(broken)).toThrow()
  })

  it('null в необязательных полях допустим', () => {
    const parsed = vacancyRowSchema.parse({ ...VACANCY, status: null, score: null })

    expect(parsed.status).toBeNull()
    expect(parsed.score).toBeNull()
  })

  it('анализ разбирается частично: модель возвращает не все поля', () => {
    const parsed = analysisSchema.parse({ score: 86, matched_skills: ['Node.js'] })

    expect(parsed.matched_skills).toEqual(['Node.js'])
    expect(parsed.red_flags).toBeUndefined()
  })

  it('провайдер отдаётся с маской ключа, а не с ключом', () => {
    const parsed = providerSchema.parse({
      id: 1,
      name: 'Anthropic',
      type: 'anthropic',
      base_url: null,
      model: 'claude-haiku-4-5',
      temperature: 0.3,
      timeout_sec: 300,
      extra_json: {},
      is_enabled: true,
      api_key_masked: 'sk-…a3f'
    })

    expect(parsed.api_key_masked).toBe('sk-…a3f')
    expect(parsed).not.toHaveProperty('api_key')
  })

  it('резюме требует обязательных полей', () => {
    expect(() => resumeSchema.parse({ id: 1, name: 'Backend' })).toThrow()
  })
})
