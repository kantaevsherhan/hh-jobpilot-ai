import { describe, expect, it } from 'vitest'
import { formatDate, formatDateTime, formatDuration } from '@/utils/format'

describe('форматирование', () => {
  it('дата показывается в привычном виде', () => {
    expect(formatDate('2026-08-20T09:20:24')).toBe('20.08.2026')
    expect(formatDateTime('2026-08-20T09:20:24')).toBe('20.08.2026 09:20')
  })

  it('отсутствующая дата даёт прочерк, а не «Invalid Date»', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDateTime(null)).toBe('—')
  })

  it('длительность прогона читается по-русски', () => {
    expect(formatDuration('2026-08-20T09:00:00', '2026-08-20T09:35:00')).toBe('35 мин')
    expect(formatDuration('2026-08-20T09:00:00', '2026-08-20T10:35:00')).toBe('1 ч 35 мин')
  })

  it('незавершённый прогон считается до текущего момента', () => {
    // ended_at пустой, пока прогон идёт
    expect(formatDuration(new Date().toISOString(), null)).toBe('0 мин')
  })
})
