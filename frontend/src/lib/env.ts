function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

const apiBaseUrl = trimTrailingSlash(
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000',
)

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY?.trim() ?? '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.trim() ?? '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim() ?? '',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET?.trim() ?? '',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID?.trim() ?? '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID?.trim() ?? '',
}
const appUrl = trimTrailingSlash(
  import.meta.env.VITE_APP_URL?.trim() || window.location.origin,
)

export const env = {
  apiBaseUrl,
  appUrl,
  firebaseConfig,
} as const

export const isFirebaseConfigured = Object.values(env.firebaseConfig).every(Boolean)
