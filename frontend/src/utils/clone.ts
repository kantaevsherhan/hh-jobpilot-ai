/**
 * Глубокая копия данных, пришедших из TanStack Query.
 *
 * structuredClone для этого не годится: Query отдаёт реактивный прокси Vue,
 * а прокси он клонировать не умеет и падает с «Proxy object could not be
 * cloned». Настройки — обычный JSON, поэтому его достаточно.
 */
export function deepCopy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}
