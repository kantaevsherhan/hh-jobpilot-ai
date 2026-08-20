import { createApp, type Component } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primevue/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

import App from '@/App.vue'
import { router } from '@/router'
import '@/style.css'
import 'primeicons/primeicons.css'

// Приглушённый сине-зелёный акцент: красный в интерфейсе зарезервирован
// под режим LIVE и ошибки, он не должен конкурировать с обычными кнопками
const preset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#f0fdfa',
      100: '#ccfbf1',
      200: '#99f6e4',
      300: '#5eead4',
      400: '#2dd4bf',
      500: '#14b8a6',
      600: '#0d9488',
      700: '#0f766e',
      800: '#115e59',
      900: '#134e4a',
      950: '#042f2e'
    }
  }
})

// App.vue для eslint остаётся нетипизированным: правила с проверкой типов
// не разбирают SFC (см. комментарий в eslint.config.mjs)
createApp(App as Component)
  .use(createPinia())
  .use(router)
  .use(VueQueryPlugin, {
    queryClientConfig: {
      defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 5_000 } }
    }
  })
  .use(PrimeVue, { theme: { preset, options: { darkModeSelector: '.dark' } } })
  .use(ToastService)
  .use(ConfirmationService)
  .directive('tooltip', Tooltip)
  .mount('#app')
