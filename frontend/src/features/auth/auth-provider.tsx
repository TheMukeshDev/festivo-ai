import {
  browserLocalPersistence,
  confirmPasswordReset,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  onIdTokenChanged,
  sendPasswordResetEmail,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  updatePassword as firebaseUpdatePassword,
  updateProfile,
  type User,
} from 'firebase/auth'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { UNAUTHORIZED_EVENT } from '@/lib/api/client'
import { setAccessTokenProvider } from '@/lib/api/token'
import { auth as firebaseAuth, firebaseConfigurationError, firebaseReady } from '@/lib/firebase/client'
import { env } from '@/lib/env'
import { AuthContext, type AuthContextValue, type AuthUser } from '@/features/auth/auth-context'

interface AuthProviderProps {
  children: ReactNode
}

function toAuthUser(user: User): AuthUser {
  return {
    id: user.uid,
    email: user.email,
    user_metadata: user.displayName ? { full_name: user.displayName } : {},
    email_confirmed_at: user.emailVerified ? user.metadata.creationTime ?? null : null,
    created_at: user.metadata.creationTime ?? new Date(0).toISOString(),
    last_sign_in_at: user.metadata.lastSignInTime ?? null,
  }
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [loading, setLoading] = useState(firebaseReady)
  const [session, setSession] = useState<AuthUser | null>(null)
  const [sessionExpired, setSessionExpired] = useState(false)
  const sessionRef = useRef<User | null>(null)

  useEffect(() => {
    setAccessTokenProvider(async () => sessionRef.current?.getIdToken() ?? null)
    return () => setAccessTokenProvider(null)
  }, [])

  useEffect(() => {
    if (!firebaseAuth) return

    let mounted = true
    const client = firebaseAuth
    void setPersistence(client, browserLocalPersistence).catch(() => {
      if (mounted) toast.error('Persistent sign-in could not be enabled.')
    })

    const unsubscribe = onIdTokenChanged(client, (user) => {
      if (!mounted) return
      sessionRef.current = user
      setSession(user ? toAuthUser(user) : null)
      setLoading(false)
    })

    const handleUnauthorized = () => {
      setSessionExpired(true)
      toast.error('Your session expired. Sign in again to continue.')
      void firebaseSignOut(client)
    }

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => {
      mounted = false
      unsubscribe()
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    if (!firebaseAuth) throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    await signInWithEmailAndPassword(firebaseAuth, email.trim(), password)
    setSessionExpired(false)
  }, [])

  const signInWithGoogle = useCallback(async () => {
    if (!firebaseAuth) throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    await signInWithPopup(firebaseAuth, new GoogleAuthProvider())
    setSessionExpired(false)
  }, [])

  const signUp = useCallback(async (email: string, password: string, fullName: string) => {
    if (!firebaseAuth) throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    const result = await createUserWithEmailAndPassword(firebaseAuth, email.trim(), password)
    await updateProfile(result.user, { displayName: fullName.trim() })
    return { needsEmailConfirmation: false }
  }, [])

  const signOut = useCallback(async () => {
    if (!firebaseAuth) return
    await firebaseSignOut(firebaseAuth)
    sessionRef.current = null
    setSession(null)
  }, [])

  const requestPasswordReset = useCallback(async (email: string) => {
    if (!firebaseAuth) throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    await sendPasswordResetEmail(firebaseAuth, email.trim(), {
      url: `${env.appUrl}/reset-password`,
      handleCodeInApp: true,
    })
  }, [])

  const updatePassword = useCallback(async (password: string, actionCode?: string) => {
    if (!firebaseAuth) throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    if (actionCode) {
      await confirmPasswordReset(firebaseAuth, actionCode, password)
      return
    }
    if (!firebaseAuth.currentUser) throw new Error('Your reset session has expired. Request a new link.')
    await firebaseUpdatePassword(firebaseAuth.currentUser, password)
  }, [])

  const clearSessionExpired = useCallback(() => setSessionExpired(false), [])

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: firebaseReady,
      configurationMessage: firebaseConfigurationError,
      loading,
      session,
      user: session,
      sessionExpired,
      signIn,
      signInWithGoogle,
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
      signInWithGoogle,
      signUp,
      signOut,
      requestPasswordReset,
      updatePassword,
      clearSessionExpired,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
