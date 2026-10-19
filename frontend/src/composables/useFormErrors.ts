import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'

/** Сообщение об ошибке поля или undefined, если поле в порядке. */
export type FieldErrors = Record<string, string | undefined>

type Notify = (messages: string[]) => void

/** Тост, если PrimeVue подключён. В юнит-тестах без приложения его нет — тогда молча. */
function toastNotifier(): Notify | undefined {
  try {
    const toast = useToast()
    return (messages) => {
      toast.add({
        severity: 'warn',
        summary: 'Форма не сохранена',
        detail: messages.join('. '),
        life: 5000
      })
    }
  } catch {
    return undefined
  }
}

/**
 * Проверка формы по нажатию «Сохранить», а не отключённой кнопкой.
 *
 * Отключённая кнопка не говорит, что именно не так. Здесь кнопка нажимается
 * всегда: при ошибках форма не отправляется, под полями появляются причины,
 * а тост перечисляет их — поле с ошибкой может быть за пределами экрана.
 * После первой попытки ошибки пересчитываются на лету и исчезают по мере правки.
 */
export function useFormErrors(
  rules: () => FieldErrors,
  notify: Notify | undefined = toastNotifier()
) {
  const attempted = ref(false)

  const errors = computed<FieldErrors>(() => (attempted.value ? rules() : {}))
  const hasErrors = computed(() => Object.values(errors.value).some(Boolean))

  /** true — можно отправлять. */
  function validate(): boolean {
    attempted.value = true
    const messages = Object.values(rules()).filter((m): m is string => Boolean(m))
    if (messages.length) notify?.(messages)
    return messages.length === 0
  }

  /** Сбросить показ ошибок, например при открытии формы заново. */
  function reset(): void {
    attempted.value = false
  }

  return { errors, hasErrors, validate, reset }
}
