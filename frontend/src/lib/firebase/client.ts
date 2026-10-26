import { getApps, initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'

import { env, isFirebaseConfigured } from '@/lib/env'

let initializationError: string | null = null
let firebaseAuth: ReturnType<typeof getAuth> | null = null

if (isFirebaseConfigured) {
  try {
    const app = getApps()[0] ?? initializeApp(env.firebaseConfig)
    firebaseAuth = getAuth(app)
  } catch (error) {
    initializationError =
      error instanceof Error ? error.message : 'Firebase could not be initialized.'
  }
} else {
  initializationError =
    'Firebase is not configured. Set the VITE_FIREBASE_* frontend environment variables.'
}

export const auth = firebaseAuth
export const firebaseConfigurationError = initializationError
export const firebaseReady = firebaseAuth !== null
