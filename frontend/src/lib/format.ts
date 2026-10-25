const DEFAULT_CURRENCY = 'INR'

export function formatMoney(
  amount: string | number | null | undefined,
  currency = DEFAULT_CURRENCY,
  options: { compact?: boolean } = {},
): string {
  if (amount === null || amount === undefined || amount === '') return '—'
  const numeric = typeof amount === 'number' ? amount : Number(amount)
  if (!Number.isFinite(numeric)) return '—'
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currency || DEFAULT_CURRENCY,
      maximumFractionDigits: 2,
      minimumFractionDigits: options.compact ? 0 : 2,
      notation: options.compact ? 'compact' : 'standard',
    }).format(numeric)
  } catch {
    return `${currency} ${numeric.toFixed(2)}`
  }
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return new Intl.NumberFormat().format(value)
}

export function formatDate(
  value: string | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium' },
): string {
  if (!value) return '—'
  const date = value instanceof Date ? value : new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(undefined, options).format(date)
}

export function formatDateTime(
  value: string | Date | null | undefined,
  timeZone?: string,
): string {
  if (!value) return '—'
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
      ...(timeZone ? { timeZone } : {}),
    }).format(date)
  } catch {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date)
  }
}

export function isPastDateTime(
  value: string | null | undefined,
  now = Date.now(),
): boolean {
  if (!value) return false
  const timestamp = new Date(value).getTime()
  return Number.isFinite(timestamp) && timestamp < now
}

export function formatRelativeDate(value: string | Date, now = new Date()): string {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const diffMs = date.getTime() - now.getTime()
  const days = Math.round(diffMs / 86_400_000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  if (Math.abs(days) < 30) return formatter.format(days, 'day')
  const months = Math.round(days / 30)
  if (Math.abs(months) < 12) return formatter.format(months, 'month')
  return formatter.format(Math.round(days / 365), 'year')
}

export function daysUntil(value: string, timeZone?: string, now = new Date()): number {
  const today = zonedDateParts(now, timeZone)
  const target = value.split('T')[0] ?? value
  const start = Date.UTC(today.year, today.month - 1, today.day)
  const [year = '0', month = '1', day = '1'] = target.split('-')
  const end = Date.UTC(Number(year), Number(month) - 1, Number(day))
  return Math.round((end - start) / 86_400_000)
}

interface ZonedParts {
  year: number
  month: number
  day: number
  hour: number
  minute: number
  second: number
}

export function zonedDateParts(date: Date, timeZone?: string): ZonedParts {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  })
  const parts = Object.fromEntries(
    formatter
      .formatToParts(date)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, part.value]),
  )
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour),
    minute: Number(parts.minute),
    second: Number(parts.second),
  }
}

export function zonedInputToUtcIso(value: string, timeZone: string): string | null {
  if (!value) return null
  const [datePart, timePart = '00:00'] = value.split('T')
  if (!datePart) return null
  const [year, month, day] = datePart.split('-').map(Number)
  const [hour, minute] = timePart.split(':').map(Number)
  if (![year, month, day, hour, minute].every((part) => Number.isFinite(part))) {
    return null
  }
  const utcGuess = Date.UTC(year!, month! - 1, day!, hour!, minute!)
  const parts = zonedDateParts(new Date(utcGuess), timeZone)
  const timezoneAsUtc = Date.UTC(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second,
  )
  const offset = timezoneAsUtc - utcGuess
  return new Date(utcGuess - offset).toISOString()
}

export function utcIsoToZonedInput(iso: string | null, timeZone: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const parts = zonedDateParts(date, timeZone)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(
    parts.minute,
  )}`
}

export function todayInputValue(timeZone?: string): string {
  const parts = zonedDateParts(new Date(), timeZone)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`
}

export function percentage(part: string, whole: string): number {
  const partNumber = Number(part)
  const wholeNumber = Number(whole)
  if (!Number.isFinite(partNumber) || !Number.isFinite(wholeNumber) || wholeNumber <= 0) {
    return 0
  }
  return Math.min(100, Math.max(0, (partNumber / wholeNumber) * 100))
}
