import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ru'

dayjs.extend(relativeTime)
dayjs.locale('ru')

export const formatDate = (value: string | null) =>
  value === null ? '—' : dayjs(value).format('DD.MM.YYYY')

export const formatDateTime = (value: string | null) =>
  value === null ? '—' : dayjs(value).format('DD.MM.YYYY HH:mm')

export const formatTime = (value: string) => dayjs(value).format('HH:mm:ss')

export const fromNow = (value: string | null) => (value === null ? '—' : dayjs(value).fromNow())

export const formatRuntimeMode = (value: string) =>
  value === 'DRY_RUN' ? 'Пробный режим' : value === 'LIVE' ? 'Реальная отправка' : value

export const formatBotMode = (value: string) =>
  value === 'MANUAL'
    ? 'Ручной'
    : value === 'SEMI_AUTO'
      ? 'Полуавтомат'
      : value === 'AUTO'
        ? 'Автомат'
        : value

export function formatDuration(from: string, to: string | null): string {
  const minutes = dayjs(to ?? undefined).diff(dayjs(from), 'minute')
  if (minutes < 60) return `${String(minutes)} мин`
  return `${String(Math.floor(minutes / 60))} ч ${String(minutes % 60)} мин`
}
