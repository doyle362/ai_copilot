const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8080'

export interface ApiResponse<T = any> {
  success: boolean
  message?: string
  data?: T
  error?: string
}

export interface Insight {
  id: string
  zone_id: string
  location_id?: string
  kind?: string
  window?: string
  narrative_text?: string
  confidence?: number
  created_at: string
}

export interface Recommendation {
  id: string
  zone_id: string
  location_id?: string
  type?: string
  proposal?: any
  rationale_text?: string
  expected_lift_json?: any
  confidence?: number
  requires_approval: boolean
  status: string
  created_at: string
}

export interface PriceChange {
  id: string
  zone_id: string
  location_id?: string
  prev_price?: number
  new_price: number
  change_pct?: number
  status: string
  created_at: string
}

class ApiClient {
  private token: string | null = null

  setToken(token: string) {
    this.token = token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${API_BASE_URL}${endpoint}`

    const headers = {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        success: true,
        data: data
      }
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async getInsights(options: { zoneId?: string; refresh?: boolean } = {}): Promise<ApiResponse<{ insights: Insight[]; total: number }>> {
    const params = new URLSearchParams()
    if (options.zoneId) params.append('zone_id', options.zoneId)
    params.append('refresh', options.refresh ? 'true' : 'false')
    params.append('limit', '100')

    const url = `/insights/?${params.toString()}`
    return this.request(url)
  }

  async getRecommendations(options: { zoneId?: string; refresh?: boolean } = {}): Promise<ApiResponse<{ recommendations: Recommendation[]; total: number }>> {
    const params = new URLSearchParams()
    if (options.zoneId) params.append('zone_id', options.zoneId)
    if (options.refresh) params.append('refresh', 'true')

    const query = params.toString()
    return this.request(`/recommendations/${query ? `?${query}` : ''}`)
  }

  async generateRecommendations(zoneId: string, context?: string): Promise<ApiResponse> {
    return this.request('/recommendations/generate', {
      method: 'POST',
      body: JSON.stringify({
        zone_id: zoneId,
        context: context || undefined,
      }),
    })
  }

  async generateExpertRecommendations(): Promise<ApiResponse> {
    return this.request('/recommendations/generate-expert', {
      method: 'POST'
    })
  }

  async getPriceChanges(zoneId?: string): Promise<ApiResponse<{ changes: PriceChange[]; total: number }>> {
    const params = new URLSearchParams()
    if (zoneId) params.append('zone_id', zoneId)

    return this.request(`/changes/?${params.toString()}`)
  }

  async applyPriceChange(changeId: string, force = false): Promise<ApiResponse> {
    return this.request('/changes/apply', {
      method: 'POST',
      body: JSON.stringify({
        change_id: changeId,
        force,
      }),
    })
  }

  async revertPriceChange(changeId: string, reason?: string): Promise<ApiResponse> {
    return this.request('/changes/revert', {
      method: 'POST',
      body: JSON.stringify({
        change_id: changeId,
        reason,
      }),
    })
  }

  async getThread(threadId: number): Promise<ApiResponse<any>> {
    return this.request(`/threads/${threadId}`)
  }

  async createThread(insightId: string | null, zoneId: string | null, threadType: string = 'insight'): Promise<ApiResponse<any>> {
    const body: any = {
      thread_type: threadType
    }

    if (insightId) body.insight_id = insightId
    if (zoneId) body.zone_id = zoneId

    return this.request('/threads/', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  async addMessage(threadId: number, role: string, content: string): Promise<ApiResponse<any>> {
    return this.request(`/threads/${threadId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        role,
        content,
      }),
    })
  }

  async getSessionCounts(timeFilter?: string, zoneFilter?: string, dayOfWeek?: string, hourStart?: number, hourEnd?: number): Promise<ApiResponse<any>> {
    const params = new URLSearchParams()
    if (timeFilter) params.append('time_filter', timeFilter)
    if (zoneFilter) params.append('zone_filter', zoneFilter)
    if (dayOfWeek) params.append('day_of_week', dayOfWeek)
    if (hourStart !== undefined) params.append('hour_start', hourStart.toString())
    if (hourEnd !== undefined) params.append('hour_end', hourEnd.toString())

    const query = params.toString() ? `?${params.toString()}` : ''
    return this.request(`/analytics/session-counts${query}`)
  }

  async getZoneSummary(): Promise<ApiResponse<any>> {
    return this.request('/analytics/zone-summary')
  }

  async getTimePatterns(zone?: string): Promise<ApiResponse<any>> {
    const params = zone ? `?zone=${zone}` : ''
    return this.request(`/analytics/time-patterns${params}`)
  }

  async getOccupancyAnalysis(): Promise<ApiResponse<any>> {
    return this.request('/analytics/occupancy-analysis')
  }

  async getKpiKnowledge(context?: string, category?: string): Promise<ApiResponse<any>> {
    const params = new URLSearchParams()
    if (context) params.append('context', context)
    if (category) params.append('category', category)

    const query = params.toString()
    return this.request(`/analytics/kpi-knowledge${query ? `?${query}` : ''}`)
  }

  async getAnalyticalPatterns(context?: string, patternType?: string, significance?: string): Promise<ApiResponse<any>> {
    const params = new URLSearchParams()
    if (context) params.append('context', context)
    if (patternType) params.append('pattern_type', patternType)
    if (significance) params.append('significance', significance)

    const query = params.toString()
    return this.request(`/analytics/analytical-patterns${query ? `?${query}` : ''}`)
  }

  async getIndustryKnowledge(context?: string, knowledgeType?: string, category?: string, industryVertical?: string): Promise<ApiResponse<any>> {
    const params = new URLSearchParams()
    if (context) params.append('context', context)
    if (knowledgeType) params.append('knowledge_type', knowledgeType)
    if (category) params.append('category', category)
    if (industryVertical) params.append('industry_vertical', industryVertical)

    const query = params.toString()
    return this.request(`/analytics/industry-knowledge${query ? `?${query}` : ''}`)
  }

  async getKpiAnalysisSuggestions(zoneData?: string): Promise<ApiResponse<any>> {
    const params = new URLSearchParams()
    if (zoneData) params.append('zone_data', zoneData)

    const query = params.toString()
    return this.request(`/analytics/kpi-analysis-suggestions${query ? `?${query}` : ''}`)
  }
}

export const apiClient = new ApiClient()
