import { createContext } from 'react'

export interface AuthUser {
  id: string
  email: string | null
  user_metadata: { full_name?: string }
  email_confirmed_at: string | null
  created_at: string
  last_sign_in_at: string | null
}

export interface AuthContextValue {
  configured: boolean
  configurationMessage: string | null
  loading: boolean
  session: AuthUser | null
  user: AuthUser | null
  sessionExpired: boolean
  signIn: (email: string, password: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<{ needsEmailConfirmation: boolean }>
  signOut: () => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
  updatePassword: (password: string, actionCode?: string) => Promise<void>
  clearSessionExpired: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
