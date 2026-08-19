import { describe, expect, it } from 'vitest'
import { AxiosError } from 'axios'
import { toMessage } from '@/api/client'

describe('toMessage', () => {
  it('достаёт человеческое сообщение из ответа бэкенда', () => {
    const error = new AxiosError('Request failed')
    error.response = {
      data: { detail: { human_message: 'Резюме не найдено' } },
      status: 404,
      statusText: 'Not Found',
      headers: {},
      config: { headers: {} }
    } as AxiosError['response']

    expect(toMessage(error)).toBe('Резюме не найдено')
  })

  it('подсказывает про make dev, когда бэкенд не отвечает', () => {
    const error = new AxiosError('Network Error', 'ERR_NETWORK')

    expect(toMessage(error)).toContain('make dev')
  })
})
