import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { UNAUTHORIZED_EVENT } from '@/lib/api/client'
import { setAccessTokenProvider } from '@/lib/api/token'
import { supabase, supabaseConfigurationError, supabaseReady } from '@/lib/supabase/client'
import { AuthContext, type AuthContextValue } from '@/features/auth/auth-context'

interface AuthProviderProps {
  children: ReactNode
}

function authErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return 'Authentication failed. Please try again.'
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [loading, setLoading] = useState(supabaseReady)
  const [session, setSession] = useState<AuthContextValue['session']>(null)
  const [sessionExpired, setSessionExpired] = useState(false)
  const sessionRef = useRef<AuthContextValue['session']>(null)

  useEffect(() => {
    setAccessTokenProvider(async () => {
      if (sessionRef.current?.access_token) {
        return sessionRef.current.access_token
      }
      if (!supabase) return null
      const { data } = await supabase.auth.getSession()
      return data.session?.access_token ?? null
    })
    return () => setAccessTokenProvider(null)
  }, [])

  useEffect(() => {
    if (!supabase) {
      return
    }

    let mounted = true
    const client = supabase

    client.auth
      .getSession()
      .then(({ data, error }) => {
        if (!mounted) return
        if (error) {
          toast.error('Your saved session could not be restored.')
        }
        sessionRef.current = data.session
        setSession(data.session)
        setLoading(false)
      })
      .catch(() => {
        if (!mounted) return
        sessionRef.current = null
        setSession(null)
        setLoading(false)
      })

    const { data: subscription } = client.auth.onAuthStateChange((event, nextSession) => {
      if (!mounted) return
      sessionRef.current = nextSession
      setSession(nextSession)
      setLoading(false)
      if (event === 'SIGNED_IN') {
        setSessionExpired(false)
      }
      if (event === 'SIGNED_OUT') {
        setSessionExpired(false)
      }
    })

    const handleUnauthorized = () => {
      setSessionExpired(true)
      toast.error('Your session expired. Sign in again to continue.')
      void client.auth.signOut()
    }

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)

    return () => {
      mounted = false
      subscription.subscription.unsubscribe()
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      throw new Error(supabaseConfigurationError ?? 'Authentication is unavailable.')
    }
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    })
    if (error) throw new Error(error.message)
    if (!data.session) {
      throw new Error('Sign-in succeeded, but no session was returned. Please try again.')
    }
    sessionRef.current = data.session
    setSession(data.session)
    setSessionExpired(false)
  }, [])

  const signUp = useCallback(async (email: string, password: string, fullName: string) => {
    if (!supabase) {
      throw new Error(supabaseConfigurationError ?? 'Authentication is unavailable.')
    }
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: { full_name: fullName.trim() },
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    if (error) throw new Error(error.message)
    return { needsEmailConfirmation: data.session === null }
  }, [])

  const signOut = useCallback(async () => {
    if (!supabase) return
    const { error } = await supabase.auth.signOut()
    if (error) throw new Error(authErrorMessage(error))
    sessionRef.current = null
    setSession(null)
  }, [])

  const requestPasswordReset = useCallback(async (email: string) => {
    if (!supabase) {
      throw new Error(supabaseConfigurationError ?? 'Authentication is unavailable.')
    }
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    if (error) throw new Error(authErrorMessage(error))
  }, [])

  const updatePassword = useCallback(async (password: string) => {
    if (!supabase) {
      throw new Error(supabaseConfigurationError ?? 'Authentication is unavailable.')
    }
    const { error } = await supabase.auth.updateUser({ password })
    if (error) throw new Error(authErrorMessage(error))
  }, [])

  const clearSessionExpired = useCallback(() => setSessionExpired(false), [])

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: supabaseReady,
      configurationMessage: supabaseConfigurationError,
      loading,
      session,
      user: session?.user ?? null,
      sessionExpired,
      signIn,
      signUp,
      signOut,
      requestPasswordReset,
      updatePassword,
      clearSessionExpired,
    }),
    [
      loading,
      session,
      sessionExpired,
      signIn,
      signUp,
      signOut,
      requestPasswordReset,
      updatePassword,
      clearSessionExpired,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
