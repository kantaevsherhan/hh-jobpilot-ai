import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUiStore } from '@/stores/ui'

describe('состояние интерфейса', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('по умолчанию боевой режим выключен', () => {
    const ui = useUiStore()

    // Защита от «настроил не то и разослал двадцать откликов» (§20)
    expect(ui.runtimeMode).toBe('DRY_RUN')
    expect(ui.isLive).toBe(false)
    expect(ui.botMode).toBe('MANUAL')
  })

  it('выбранное резюме и режимы переживают перезагрузку', async () => {
    const ui = useUiStore()
    ui.resumeId = 7
    ui.runtimeMode = 'LIVE'
    ui.botMode = 'AUTO'
    await Promise.resolve()

    setActivePinia(createPinia())
    const restored = useUiStore()

    expect(restored.resumeId).toBe(7)
    expect(restored.runtimeMode).toBe('LIVE')
    expect(restored.botMode).toBe('AUTO')
  })

  it('повреждённое хранилище не роняет приложение', () => {
    localStorage.setItem('jobpilot.ui', '{это не json')

    const ui = useUiStore()

    expect(ui.resumeId).toBeNull()
    expect(ui.runtimeMode).toBe('DRY_RUN')
  })

  it('частично сохранённое состояние дополняется дефолтами', () => {
    // Так выглядит хранилище, записанное прошлой версией приложения
    localStorage.setItem('jobpilot.ui', JSON.stringify({ resumeId: 3 }))

    const ui = useUiStore()

    expect(ui.resumeId).toBe(3)
    expect(ui.runtimeMode).toBe('DRY_RUN')
    expect(ui.sidebarCollapsed).toBe(false)
  })

  it('hasResume отражает выбор резюме', () => {
    const ui = useUiStore()

    expect(ui.hasResume).toBe(false)
    ui.resumeId = 1
    expect(ui.hasResume).toBe(true)
  })
})
