import { MessageSquare, TrendingUp, Clock, AlertCircle } from 'lucide-react'
import type { Insight } from '../api'

interface InsightCardProps {
  insight: Insight
  onDiscuss?: (insight: Insight) => void
}

export default function InsightCard({ insight, onDiscuss }: InsightCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getKindIcon = (kind?: string) => {
    switch (kind) {
      case 'performance':
        return <TrendingUp className="w-4 h-4 text-level-green" />
      case 'alert':
        return <AlertCircle className="w-4 h-4 text-level-amber" />
      default:
        return <Clock className="w-4 h-4 text-level-blue" />
    }
  }

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-gray-500'
    if (confidence >= 0.8) return 'text-level-green'
    if (confidence >= 0.6) return 'text-level-amber'
    return 'text-level-red'
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          {getKindIcon(insight.kind)}
          <span className="text-sm font-medium text-gray-900 capitalize">
            {insight.kind || 'General'}
          </span>
          {insight.window && (
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {insight.window}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {insight.confidence && (
            <span className={`text-xs font-medium ${getConfidenceColor(insight.confidence)}`}>
              {Math.round(insight.confidence * 100)}% confidence
            </span>
          )}
          <span className="text-xs text-gray-500">
            {formatDate(insight.created_at)}
          </span>
        </div>
      </div>

      <div className="mb-3">
        <p className="text-sm text-gray-700 leading-relaxed">
          {insight.narrative_text || 'No description available'}
        </p>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 text-xs text-gray-500">
          <span>Zone: {insight.zone_id}</span>
        </div>

        {onDiscuss && (
          <button
            onClick={() => onDiscuss(insight)}
            className="flex items-center space-x-1 text-sm text-level-blue hover:text-level-blue/80 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            <span>Discuss</span>
          </button>
        )}
      </div>
    </div>
  )
}