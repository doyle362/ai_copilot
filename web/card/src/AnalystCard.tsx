import { useState, useEffect } from 'react'
import {
  Sparkles,
  TrendingUp,
  Settings,
  Play,
  RotateCcw,
  RefreshCw,
  AlertCircle,
  MessageCircle
} from 'lucide-react'
import { apiClient, type Insight, type Recommendation, type PriceChange } from './api'
import { authManager } from './auth'
import InsightCard from './components/InsightCard'
import ThreadDrawer from './components/ThreadDrawer'
import GeneralChatDrawer from './components/GeneralChatDrawer'
import MemoryBadge from './components/MemoryBadge'
import GuardrailPills from './components/GuardrailPills'

export default function AnalystCard() {
  const [insights, setInsights] = useState<Insight[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [priceChanges, setPriceChanges] = useState<PriceChange[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isGeneralChatOpen, setIsGeneralChatOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'insights' | 'recommendations' | 'changes'>('insights')

  // Configuration - automatic token management
  const [config] = useState({
    mode: 'review' as 'review' | 'approve' | 'execute'
  })

  useEffect(() => {
    // Initialize automatic token management and load data
    const initializeAuth = async () => {
      try {
        const token = await authManager.getValidToken()
        apiClient.setToken(token)
        await loadData()
      } catch (error) {
        console.error('Failed to initialize authentication:', error)
        setError('Authentication failed. Please refresh the page.')
      }
    }

    initializeAuth()

    // Cleanup on unmount
    return () => {
      authManager.destroy()
    }
  }, [])

  const loadData = async ({ refresh = false }: { refresh?: boolean } = {}) => {
    setIsLoading(true)
    setError(null)

    try {
      // Load insights first so daily refresh completes before dependent requests
      const insightsRes = await apiClient.getInsights({ refresh })

      // Load recommendations and price changes in parallel once insights are available
      const [recsRes, changesRes] = await Promise.all([
        apiClient.getRecommendations({ refresh }),
        apiClient.getPriceChanges(),
      ])

      if (insightsRes.success && insightsRes.data) {
        console.log(`🔥 Fresh insights loaded: ${insightsRes.data.insights?.length || 0} total, zones:`,
          [...new Set(insightsRes.data.insights?.map(i => i.zone_id) || [])].sort())
        setInsights(insightsRes.data.insights || [])
      }

      if (recsRes.success && recsRes.data) {
        // Sort recommendations by expected ROI/return (highest first)
        const sortedRecs = (recsRes.data.recommendations || []).sort((a, b) => {
          const aReturn = a.expected_lift_json?.expected_return || a.expected_lift_json?.revenue_lift || 0
          const bReturn = b.expected_lift_json?.expected_return || b.expected_lift_json?.revenue_lift || 0
          return bReturn - aReturn
        })
        setRecommendations(sortedRecs)
      }

      if (changesRes.success && changesRes.data) {
        setPriceChanges(changesRes.data.changes || [])
      }

      // Check for any errors
      const hasErrors = [insightsRes, recsRes, changesRes].some(res => !res.success)
      if (hasErrors) {
        const errorMessages = [insightsRes, recsRes, changesRes]
          .filter(res => !res.success)
          .map(res => res.error)
          .join('; ')
        setError(errorMessages)
      }
    } catch (err) {
      setError('Failed to load data from API')
      console.error('Load data error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDiscussInsight = (insight: Insight) => {
    setSelectedInsight(insight)
    setIsDrawerOpen(true)
  }

  const handleGenerateRecommendations = async () => {
    setIsLoading(true)
    try {
      // Generate expert recommendations for all zones using parking industry knowledge
      const response = await apiClient.generateExpertRecommendations()
      if (response.success) {
        // Reload recommendations
        setTimeout(() => {
          loadData()
        }, 3000) // Give time for background generation
      } else {
        setError(response.error || 'Failed to generate expert recommendations')
      }
    } catch (err) {
      setError('Failed to generate expert recommendations')
    } finally {
      setIsLoading(false)
    }
  }

  const handleApplyChange = async (changeId: string) => {
    if (!confirm('Are you sure you want to apply this price change?')) return

    try {
      const response = await apiClient.applyPriceChange(changeId)
      if (response.success) {
        loadData() // Reload to get updated status
      } else {
        setError(response.error || 'Failed to apply change')
      }
    } catch (err) {
      setError('Failed to apply change')
    }
  }

  const handleRevertChange = async (changeId: string) => {
    if (!confirm('Are you sure you want to revert this price change?')) return

    try {
      const response = await apiClient.revertPriceChange(changeId)
      if (response.success) {
        loadData() // Reload to get updated status
      } else {
        setError(response.error || 'Failed to revert change')
      }
    } catch (err) {
      setError('Failed to revert change')
    }
  }

  const getTabCount = (tab: string) => {
    switch (tab) {
      case 'insights':
        return insights.length
      case 'recommendations':
        return recommendations.length
      case 'changes':
        return priceChanges.length
      default:
        return 0
    }
  }

  if (isLoading && insights.length === 0) {
    return (
      <div className="w-full max-w-4xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-level-blue mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Level Analyst</h2>
            <p className="text-gray-600">Loading insights and recommendations...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="lg-page-header p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Sparkles className="w-8 h-8 text-level-blue" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Level Analyst Dashboard</h1>
              <p className="text-gray-600">All Zones • Mode: {config.mode} • ROI Prioritized</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsGeneralChatOpen(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
            >
              <MessageCircle className="w-4 h-4" />
              <span>Analyst Chat</span>
            </button>

            <button
              onClick={() => loadData({ refresh: true })}
              disabled={isLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={handleGenerateRecommendations}
              disabled={isLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-level-blue text-white rounded-lg hover:bg-level-blue/90 disabled:opacity-50 transition-colors"
            >
              <TrendingUp className="w-4 h-4" />
              <span>Generate Expert Recs</span>
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Error:</span>
            </div>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        )}

        {/* Memory and Guardrails */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-gray-700">Active Memory:</span>
            <MemoryBadge kind="canonical" count={3} />
            <MemoryBadge kind="context" count={7} />
            <MemoryBadge kind="exception" count={1} />
          </div>

          <GuardrailPills
            guardrails={[
              { name: 'Price Limits', status: 'pass' },
              { name: 'Change Rate', status: 'pass' },
              { name: 'Approval Required', status: 'warn', message: 'Manual approval enabled' },
            ]}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'insights', label: 'Insights', icon: Sparkles },
              { id: 'recommendations', label: 'Recommendations', icon: TrendingUp },
              { id: 'changes', label: 'Price Changes', icon: Settings },
            ].map((tab) => {
              const Icon = tab.icon
              const count = getTabCount(tab.id)
              const isActive = activeTab === tab.id

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    isActive
                      ? 'border-level-blue text-level-blue'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                  {count > 0 && (
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        isActive ? 'bg-level-blue text-white' : 'bg-gray-200 text-gray-700'
                      }`}
                    >
                      {count}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'insights' && (
            <div className="space-y-4">
              {insights.length === 0 ? (
                <div className="text-center py-12">
                  <Sparkles className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No insights yet</h3>
                  <p className="text-gray-500">
                    Insights will appear here as the system analyzes your parking data.
                  </p>
                </div>
              ) : (
                insights.map((insight) => (
                  <InsightCard
                    key={insight.id}
                    insight={insight}
                    onDiscuss={handleDiscussInsight}
                  />
                ))
              )}
            </div>
          )}

          {activeTab === 'recommendations' && (
            <div className="space-y-4">
              {recommendations.length === 0 ? (
                <div className="text-center py-12">
                  <TrendingUp className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No recommendations</h3>
                  <p className="text-gray-500 mb-4">
                    Click "Generate Expert Recs" to create industry-expert pricing recommendations with revenue estimates.
                  </p>
                  <button
                    onClick={handleGenerateRecommendations}
                    disabled={isLoading}
                    className="px-4 py-2 bg-level-blue text-white rounded-lg hover:bg-level-blue/90 disabled:opacity-50"
                  >
                    Generate Expert Recommendations
                  </button>
                </div>
              ) : (
                recommendations.map((rec) => (
                  <div
                    key={rec.id}
                    className="bg-gray-50 rounded-lg border border-gray-200 p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="font-medium text-gray-900 capitalize">
                            {rec.type || 'Price Adjustment'}
                          </h4>
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                            Zone: {rec.zone_id}
                          </span>
                          {rec.expected_lift_json?.expected_return && (
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full font-medium">
                              ${Math.round(rec.expected_lift_json.expected_return)} ROI
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{rec.rationale_text}</p>
                      </div>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          rec.status === 'approved'
                            ? 'bg-green-100 text-green-800'
                            : rec.status === 'rejected'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {rec.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center space-x-4">
                        {rec.confidence && (
                          <span>Confidence: {Math.round(rec.confidence * 100)}%</span>
                        )}
                        <span>{new Date(rec.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'changes' && (
            <div className="space-y-4">
              {priceChanges.length === 0 ? (
                <div className="text-center py-12">
                  <Settings className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No price changes</h3>
                  <p className="text-gray-500">
                    Price changes will appear here when recommendations are applied.
                  </p>
                </div>
              ) : (
                priceChanges.map((change) => (
                  <div
                    key={change.id}
                    className="bg-gray-50 rounded-lg border border-gray-200 p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="font-medium text-gray-900">
                            ${change.prev_price?.toFixed(2) || '0.00'} → ${change.new_price.toFixed(2)}
                          </span>
                          {change.change_pct && (
                            <span
                              className={`text-sm font-medium ${
                                change.change_pct > 0 ? 'text-green-600' : 'text-red-600'
                              }`}
                            >
                              ({change.change_pct > 0 ? '+' : ''}
                              {(change.change_pct * 100).toFixed(1)}%)
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">Zone: {change.zone_id}</p>
                      </div>

                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${
                            change.status === 'applied'
                              ? 'bg-green-100 text-green-800'
                              : change.status === 'reverted'
                              ? 'bg-gray-100 text-gray-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {change.status}
                        </span>

                        {config.mode === 'execute' && (
                          <div className="flex space-x-1">
                            {change.status === 'pending' && (
                              <button
                                onClick={() => handleApplyChange(change.id)}
                                className="p-1 text-green-600 hover:bg-green-100 rounded"
                                title="Apply change"
                              >
                                <Play className="w-4 h-4" />
                              </button>
                            )}
                            {change.status === 'applied' && (
                              <button
                                onClick={() => handleRevertChange(change.id)}
                                className="p-1 text-red-600 hover:bg-red-100 rounded"
                                title="Revert change"
                              >
                                <RotateCcw className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-gray-500">
                      {new Date(change.created_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Thread Drawer */}
      <ThreadDrawer
        insight={selectedInsight}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />

      {/* General Chat Drawer */}
      <GeneralChatDrawer
        isOpen={isGeneralChatOpen}
        onClose={() => setIsGeneralChatOpen(false)}
      />
    </div>
  )
}
