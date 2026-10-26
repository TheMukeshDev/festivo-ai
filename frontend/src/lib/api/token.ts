type TokenProvider = () => Promise<string | null>

let tokenProvider: TokenProvider | null = null

export function setAccessTokenProvider(provider: TokenProvider | null): void {
  tokenProvider = provider
}

export async function resolveAccessToken(): Promise<string | null> {
  return tokenProvider ? tokenProvider() : null
}
