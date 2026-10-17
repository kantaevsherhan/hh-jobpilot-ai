import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppSidebar from '@/layouts/AppSidebar.vue'
import { useUiStore } from '@/stores/ui'

describe('боковое меню', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('сворачивается и оставляет ссылки доступными по названию', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/dashboard', component: { template: '<div />' } }]
    })
    await router.push('/dashboard')
    await router.isReady()

    const wrapper = mount(AppSidebar, {
      global: { plugins: [router], directives: { tooltip: () => undefined } }
    })
    const toggle = wrapper.get('button[aria-label="Свернуть меню"]')
    await toggle.trigger('click')

    expect(wrapper.get('aside').classes()).toContain('w-16')
    expect(wrapper.get('button[aria-label="Развернуть меню"]')).toBeTruthy()
    expect(wrapper.get('a[aria-label="Мои резюме"]').attributes('href')).toBe('/resumes')
    expect(wrapper.text()).not.toContain('Поисковые профили')

    await wrapper.get('button[aria-label="Развернуть меню"]').trigger('click')
    expect(wrapper.get('aside').classes()).toContain('w-60')
    expect(wrapper.text()).toContain('Поисковые профили')
    expect(useUiStore().sidebarCollapsed).toBe(false)
  })
})
