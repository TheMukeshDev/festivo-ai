import { createContext } from 'react'
import type { Session, User } from '@supabase/supabase-js'

export interface AuthContextValue {
  configured: boolean
  configurationMessage: string | null
  loading: boolean
  session: Session | null
  user: User | null
  sessionExpired: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<{ needsEmailConfirmation: boolean }>
  signOut: () => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
  updatePassword: (password: string) => Promise<void>
  clearSessionExpired: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
