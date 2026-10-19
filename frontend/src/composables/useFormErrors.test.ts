import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'
import { useFormErrors } from '@/composables/useFormErrors'

describe('useFormErrors', () => {
  const setup = () => {
    const form = reactive({ name: '' })
    const validation = useFormErrors(() => ({
      name: form.name.trim() ? undefined : 'Укажите название'
    }))
    return { form, ...validation }
  }

  it('до первой попытки ошибки не показываются', () => {
    const { errors } = setup()

    expect(errors.value.name).toBeUndefined()
  })

  it('неверная форма не проходит и показывает причину', () => {
    const { errors, validate } = setup()

    expect(validate()).toBe(false)
    expect(errors.value.name).toBe('Укажите название')
  })

  it('ошибка исчезает, как только поле исправлено', () => {
    const { form, errors, validate } = setup()
    validate()

    form.name = 'Anti-AI'

    expect(errors.value.name).toBeUndefined()
    expect(validate()).toBe(true)
  })

  it('при ошибке перечисляет все причины одним уведомлением', () => {
    const form = reactive({ name: '', content: '' })
    const shown: string[][] = []
    const { validate } = useFormErrors(
      () => ({
        name: form.name ? undefined : 'Укажите название',
        content: form.content ? undefined : 'Вставьте текст'
      }),
      (messages) => shown.push(messages)
    )

    validate()

    expect(shown).toEqual([['Укажите название', 'Вставьте текст']])
  })

  it('reset прячет ошибки при новом открытии формы', () => {
    const { errors, validate, reset } = setup()
    validate()

    reset()

    expect(errors.value.name).toBeUndefined()
  })
})
