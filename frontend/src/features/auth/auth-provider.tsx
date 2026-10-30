import {
  confirmPasswordReset,
  createUserWithEmailAndPassword,
  getRedirectResult,
  GoogleAuthProvider,
  onIdTokenChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  signOut as firebaseSignOut,
  updatePassword as firebaseUpdatePassword,
  updateProfile,
  type User,
} from 'firebase/auth'
import type { FirebaseError } from 'firebase/app'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { UNAUTHORIZED_EVENT } from '@/lib/api/client'
import { setAccessTokenProvider } from '@/lib/api/token'
import {
  auth as firebaseAuth,
  firebaseConfigurationError,
  firebaseReady,
} from '@/lib/firebase/client'
import { env } from '@/lib/env'
import {
  AuthContext,
  type AuthContextValue,
  type AuthUser,
} from '@/features/auth/auth-context'

interface AuthProviderProps {
  children: ReactNode
}

function toAuthUser(user: User): AuthUser {
  return {
    id: user.uid,
    email: user.email,
    user_metadata: user.displayName ? { full_name: user.displayName } : {},
    email_confirmed_at: user.emailVerified ? (user.metadata.creationTime ?? null) : null,
    created_at: user.metadata.creationTime ?? new Date(0).toISOString(),
    last_sign_in_at: user.metadata.lastSignInTime ?? null,
  }
}

function getAuthErrorMessage(error: unknown, fallback: string): string {
  if (!(error as FirebaseError)?.code) {
    return error instanceof Error ? error.message : fallback
  }

  switch ((error as FirebaseError).code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
      return 'The email or password is incorrect.'
    case 'auth/user-not-found':
      return 'No account was found for this email address.'
    case 'auth/email-already-in-use':
      return 'An account already exists for this email address. Sign in instead.'
    case 'auth/popup-blocked':
      return 'Google sign-in was blocked by the browser. Please allow redirects and try again.'
    case 'auth/unauthorized-domain':
      return 'This website is not authorized in Firebase Authentication settings.'
    case 'auth/too-many-requests':
      return 'Too many attempts. Wait a few minutes before trying again.'
    case 'auth/invalid-action-code':
    case 'auth/expired-action-code':
      return 'This password reset link is invalid or has expired. Request a new one.'
    case 'auth/missing-email':
      return 'Enter your email address before requesting a reset link.'
    case 'auth/operation-not-allowed':
      return 'Email/password authentication is not enabled in Firebase Authentication.'
    default:
      return error instanceof Error ? error.message : fallback
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
    // Keep the loading gate closed until BOTH the restored session and any
    // pending Google redirect are resolved. Otherwise a returning Google user
    // briefly lands on the sign-in page before the workspace.
    let sessionResolved = false
    const shouldResolveRedirect = window.location.pathname === '/auth/callback'
    let redirectResolved = !shouldResolveRedirect
    const releaseGate = () => {
      if (mounted && sessionResolved && redirectResolved) setLoading(false)
    }
    const gateTimer = window.setTimeout(() => {
      sessionResolved = true
      redirectResolved = true
      releaseGate()
    }, 8000)
    const client = firebaseAuth

    const unsubscribe = onIdTokenChanged(client, (user) => {
      if (!mounted) return
      sessionRef.current = user
      setSession(user ? toAuthUser(user) : null)
      sessionResolved = true
      releaseGate()
    })

    if (shouldResolveRedirect) {
      // The cross-site redirect event can be lost under Chrome's storage
      // partitioning; never let it hang silently — resolve after a bounded wait
      // and tell the user instead of bouncing them back to the form.
      const redirectWaitMs = 12_000
      const redirectTimeout = new Promise<never>((_, reject) => {
        window.setTimeout(
          () => reject(new Error('Google sign-in did not finish. Please try again.')),
          redirectWaitMs,
        )
      })
      void Promise.race([getRedirectResult(client), redirectTimeout])
        .then((result) => {
          if (!mounted) return
          if (result?.user) {
            sessionRef.current = result.user
            setSession(toAuthUser(result.user))
          }
        })
        .catch((error: unknown) => {
          if (mounted) toast.error(getAuthErrorMessage(error, 'Google sign-in failed.'))
        })
        .finally(() => {
          if (!mounted) return
          redirectResolved = true
          releaseGate()
        })
    } else {
      releaseGate()
    }

    const handleUnauthorized = () => {
      setSessionExpired(true)
      toast.error('Your session expired. Sign in again to continue.')
      void firebaseSignOut(client)
    }

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => {
      mounted = false
      window.clearTimeout(gateTimer)
      unsubscribe()
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    if (!firebaseAuth)
      throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    try {
      await signInWithEmailAndPassword(firebaseAuth, email.trim(), password)
    } catch (error) {
      throw new Error(getAuthErrorMessage(error, 'Could not sign in.'))
    }
    setSessionExpired(false)
  }, [])

  const signInWithGoogle = useCallback(async () => {
    if (!firebaseAuth)
      throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    const provider = new GoogleAuthProvider()
    try {
      // Popup works reliably on desktop: the result comes back through the
      // opener window instead of the cross-site redirect iframe handoff, which
      // Chrome's storage partitioning can silently drop (app on vercel.app,
      // authDomain on firebaseapp.com).
      await signInWithPopup(firebaseAuth, provider)
    } catch (error) {
      const code = (error as FirebaseError)?.code
      if (code === 'auth/popup-blocked' || code === 'auth/cancelled-popup-request') {
        // Browser blocked the popup — fall back to the full-page redirect.
        await signInWithRedirect(firebaseAuth, provider)
      } else {
        throw error
      }
    }
    setSessionExpired(false)
  }, [])

  const signUp = useCallback(async (email: string, password: string, fullName: string) => {
    if (!firebaseAuth)
      throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    let result: Awaited<ReturnType<typeof createUserWithEmailAndPassword>>
    try {
      result = await createUserWithEmailAndPassword(firebaseAuth, email.trim(), password)
    } catch (error) {
      throw new Error(getAuthErrorMessage(error, 'Could not create the account.'))
    }
    try {
      await updateProfile(result.user, { displayName: fullName.trim() })
    } catch {
      // The account exists even if the display name could not be saved.
    }
    return { needsEmailConfirmation: false }
  }, [])

  const signOut = useCallback(async () => {
    if (!firebaseAuth) return
    await firebaseSignOut(firebaseAuth)
    sessionRef.current = null
    setSession(null)
  }, [])

  const requestPasswordReset = useCallback(async (email: string) => {
    if (!firebaseAuth)
      throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    try {
      await sendPasswordResetEmail(firebaseAuth, email.trim(), {
        url: `${env.appUrl}/reset-password`,
        handleCodeInApp: true,
      })
    } catch (error) {
      throw new Error(getAuthErrorMessage(error, 'Could not send the reset email.'))
    }
  }, [])

  const updatePassword = useCallback(async (password: string, actionCode?: string) => {
    if (!firebaseAuth)
      throw new Error(firebaseConfigurationError ?? 'Authentication is unavailable.')
    if (actionCode) {
      try {
        await confirmPasswordReset(firebaseAuth, actionCode, password)
      } catch (error) {
        throw new Error(getAuthErrorMessage(error, 'Could not update your password.'))
      }
      return
    }
    if (!firebaseAuth.currentUser)
      throw new Error('Your reset session has expired. Request a new link.')
    try {
      await firebaseUpdatePassword(firebaseAuth.currentUser, password)
    } catch (error) {
      throw new Error(getAuthErrorMessage(error, 'Could not update your password.'))
    }
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
