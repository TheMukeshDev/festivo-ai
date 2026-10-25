import { supabase } from '@/lib/supabase/client'

type TokenProvider = () => Promise<string | null>

let tokenProvider: TokenProvider | null = null

export function setAccessTokenProvider(provider: TokenProvider | null): void {
  tokenProvider = provider
}

export async function resolveAccessToken(): Promise<string | null> {
  if (tokenProvider) {
    return tokenProvider()
  }
  if (!supabase) {
    return null
  }
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
