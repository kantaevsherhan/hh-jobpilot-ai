import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'
import { deepCopy } from '@/utils/clone'

describe('deepCopy', () => {
  it('копирует реактивный прокси, на котором падал structuredClone', () => {
    // Экран задержек падал с «Proxy object could not be cloned»:
    // TanStack Query отдаёт данные завёрнутыми в реактивный прокси Vue
    const proxied = reactive({ ranges: { between_vacancies: [3, 8] }, speed_multiplier: 1 })

    const copy = deepCopy(proxied)
    copy.ranges.between_vacancies[0] = 99

    expect(proxied.ranges.between_vacancies[0]).toBe(3)
    expect(copy.speed_multiplier).toBe(1)
  })

  it('копия не делит вложенные объекты с оригиналом', () => {
    const source = { ranges: { page_load: [1, 2.5] } }

    const copy = deepCopy(source)
    copy.ranges.page_load.push(9)

    expect(source.ranges.page_load).toHaveLength(2)
  })
})
