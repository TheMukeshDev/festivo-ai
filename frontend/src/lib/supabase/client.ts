import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import { env, isSupabaseConfigured } from '@/lib/env'

let client: SupabaseClient | null = null
let initializationError: string | null = null

if (isSupabaseConfigured) {
  try {
    client = createClient(env.supabaseUrl, env.supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: 'pkce',
      },
    })
  } catch (error) {
    initializationError =
      error instanceof Error ? error.message : 'Supabase could not be initialized.'
    client = null
  }
} else {
  initializationError =
    'Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.'
}

export const supabase = client
export const supabaseConfigurationError = initializationError
export const supabaseReady = client !== null
