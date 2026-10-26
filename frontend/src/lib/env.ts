function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

const apiBaseUrl = trimTrailingSlash(
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000',
)

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim() ?? ''
const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY?.trim() ||
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() ||
  ''
const appUrl = trimTrailingSlash(
  import.meta.env.VITE_APP_URL?.trim() || window.location.origin,
)

export const env = {
  apiBaseUrl,
  appUrl,
  supabaseUrl,
  supabaseAnonKey,
} as const

export const isSupabaseConfigured = Boolean(env.supabaseUrl && env.supabaseAnonKey)
