/**
 * Automatic JWT Token Management
 *
 * This module handles automatic token generation, refresh, and expiration management
 * to avoid the hardcoded JWT token issues.
 */

interface TokenResponse {
  token: string
  expires_at: string
  zone_access: string[]
  zones_with_data: number
}

interface TokenInfo {
  token: string
  expiresAt: Date
  zoneAccess: string[]
}

class AuthManager {
  private currentToken: TokenInfo | null = null
  private refreshTimer: number | null = null
  private readonly API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'

  /**
   * Get a valid token, refreshing if necessary
   */
  async getValidToken(): Promise<string> {
    // If we have a token and it's not expired (with 5 min buffer), use it
    if (this.currentToken && this.isTokenValid()) {
      return this.currentToken.token
    }

    // Otherwise, get a fresh token
    return await this.refreshToken()
  }

  /**
   * Check if current token is valid (not expired with 5 min buffer)
   */
  private isTokenValid(): boolean {
    if (!this.currentToken) return false

    const now = new Date()
    const expiresWithBuffer = new Date(this.currentToken.expiresAt.getTime() - (5 * 60 * 1000)) // 5 min buffer

    return now < expiresWithBuffer
  }

  /**
   * Fetch a fresh token from the backend
   */
  async refreshToken(): Promise<string> {
    try {
      console.log('🔄 Refreshing JWT token...')

      const response = await fetch(`${this.API_BASE}/auth/generate-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to generate token: ${response.status}`)
      }

      const data: TokenResponse = await response.json()

      this.currentToken = {
        token: data.token,
        expiresAt: new Date(data.expires_at),
        zoneAccess: data.zone_access
      }

      console.log(`✅ Token refreshed. Access to ${data.zones_with_data} zones. Expires: ${data.expires_at}`)

      // Schedule next refresh (refresh when 90% of time has passed)
      this.scheduleRefresh()

      return this.currentToken.token

    } catch (error) {
      console.error('❌ Token refresh failed:', error)
      throw new Error('Failed to refresh authentication token')
    }
  }

  /**
   * Schedule automatic token refresh
   */
  private scheduleRefresh() {
    if (this.refreshTimer) {
      window.clearTimeout(this.refreshTimer)
    }

    if (!this.currentToken) return

    const now = new Date()
    const expiresAt = this.currentToken.expiresAt
    const totalLifetime = expiresAt.getTime() - now.getTime()

    // Refresh when 90% of the token lifetime has passed
    const refreshIn = totalLifetime * 0.9

    console.log(`⏰ Next token refresh scheduled in ${Math.round(refreshIn / 1000 / 60)} minutes`)

    this.refreshTimer = window.setTimeout(() => {
      this.refreshToken().catch(console.error)
    }, refreshIn)
  }

  /**
   * Get information about current token
   */
  getTokenInfo(): TokenInfo | null {
    return this.currentToken
  }

  /**
   * Clean up timers
   */
  destroy() {
    if (this.refreshTimer) {
      window.clearTimeout(this.refreshTimer)
      this.refreshTimer = null
    }
  }
}

// Create singleton instance
export const authManager = new AuthManager()

/**
 * Enhanced API client with automatic token management
 */
export class AuthenticatedApiClient {
  private readonly apiClient: any

  constructor(apiClient: any) {
    this.apiClient = apiClient
  }

  /**
   * Initialize with automatic token management
   */
  async initialize() {
    try {
      const token = await authManager.getValidToken()
      this.apiClient.setToken(token)

      console.log('🔐 API client initialized with automatic token management')
    } catch (error) {
      console.error('Failed to initialize authenticated API client:', error)
      throw error
    }
  }

  /**
   * Make an authenticated request (automatically handles token refresh)
   */
  async makeRequest<T>(requestFn: () => Promise<T>): Promise<T> {
    try {
      // Ensure we have a valid token
      const token = await authManager.getValidToken()
      this.apiClient.setToken(token)

      return await requestFn()
    } catch (error) {
      // If it's an auth error, try refreshing token once
      if (this.isAuthError(error)) {
        console.log('🔄 Authentication error detected, refreshing token...')
        const newToken = await authManager.refreshToken()
        this.apiClient.setToken(newToken)
        return await requestFn()
      }

      throw error
    }
  }

  private isAuthError(error: any): boolean {
    return error?.message?.includes('401') ||
           error?.message?.includes('Unauthorized') ||
           error?.message?.includes('JWT')
  }
}