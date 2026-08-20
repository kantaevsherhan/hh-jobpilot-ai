import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SalaryCell from '@/components/SalaryCell.vue'
import ScoreBadge from '@/components/ScoreBadge.vue'

describe('SalaryCell', () => {
  // Разряды разделяются неразрывным пробелом, для сравнения приводим к обычному
  const render = (props: Record<string, unknown>) =>
    mount(SalaryCell, {
      props: { from: null, to: null, currency: null, gross: null, ...props }
    })
      .text()
      .replace(/\u00a0/g, ' ')

  it('показывает вилку со знаком валюты', () => {
    expect(render({ from: 700000, to: 900000, currency: 'KZT' })).toContain('₸')
    expect(render({ from: 700000, to: 900000, currency: 'KZT' })).toContain('900 000')
  })

  it('различает «от» и «до»', () => {
    expect(render({ from: 700000, currency: 'KZT' })).toContain('от')
    expect(render({ to: 900000, currency: 'KZT' })).toContain('до')
  })

  it('рубли приходят кодом RUR и показываются рублём', () => {
    expect(render({ from: 100000, currency: 'RUR' })).toContain('₽')
  })

  it('помечает зарплату до вычета налога', () => {
    expect(render({ from: 700000, currency: 'KZT', gross: true })).toContain('до вычета')
    expect(render({ from: 700000, currency: 'KZT', gross: false })).not.toContain('до вычета')
  })

  it('не выдумывает сумму, когда её нет', () => {
    expect(render({})).toContain('не указана')
  })

  it('незнакомую валюту показывает как есть, а не молчит', () => {
    expect(render({ from: 1000, currency: 'GBP' })).toContain('GBP')
  })
})

describe('ScoreBadge', () => {
  const render = (score: number | null) => mount(ScoreBadge, { props: { score } })

  it('показывает прочерк, если оценки ещё нет', () => {
    expect(render(null).text()).toBe('—')
  })

  it('выделяет оценку выше порога автоотклика', () => {
    expect(render(95).classes().join(' ')).toContain('teal')
  })

  it('приглушает оценку ниже порога отбора', () => {
    expect(render(40).classes().join(' ')).toContain('slate-400')
  })
})
