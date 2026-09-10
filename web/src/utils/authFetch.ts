/**
 * Authenticated fetch wrapper — automatically attaches session token.
 */

const TOKEN_KEY = 'peppa_session_token'

function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

export function getSessionToken(): string | null {
  return getToken()
}

/**
 * authFetch — wraps fetch with session token for write operations.
 * For read-only GET requests, token is optional (but included if present).
 */
export async function authFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const token = getToken()
  const headers = new Headers(options.headers)
  if (token) {
    headers.set('X-Session-Token', token)
  }
  return fetch(url, { ...options, headers })
}
