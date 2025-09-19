import { useState, useEffect, useRef } from 'react'
import { X, Send, User, Bot, AlertCircle } from 'lucide-react'
import { apiClient, type Insight } from '../api'

interface ThreadDrawerProps {
  insight: Insight | null
  isOpen: boolean
  onClose: () => void
}

interface Message {
  id: number
  role: string
  content: string
  created_at: string
}

interface TimeParseResult {
  dayOfWeek?: string
  hourStart?: number
  hourEnd?: number
  timeDescription: string
}

interface IntentAnalysis {
  requiresData: boolean
  dataType: 'sessions' | 'duration' | 'revenue' | 'occupancy' | 'general'
  timeFilter?: string
  zoneFilter?: string
  analysisType: 'count' | 'average' | 'breakdown' | 'total' | 'comparison'
  responseStyle: 'simple' | 'detailed' | 'analytical'
  conversationType: 'data' | 'guidance' | 'insight' | 'casual'
  timeInfo?: TimeParseResult
}

export default function ThreadDrawer({ insight, isOpen, onClose }: ThreadDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isAiThinking, setIsAiThinking] = useState(false)
  const [threadId, setThreadId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen && insight) {
      loadOrCreateThread()
    } else {
      // Reset state when drawer closes
      setMessages([])
      setThreadId(null)
      setNewMessage('')
      setError(null)
      setIsAiThinking(false)
    }
  }, [isOpen, insight])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isAiThinking])

  const loadOrCreateThread = async () => {
    if (!insight) return

    setIsLoading(true)
    setError(null)

    try {
      // First try to create a thread for this insight
      const createResponse = await apiClient.createThread(insight.id, insight.zone_id)

      if (createResponse.success && createResponse.data) {
        const threadData = createResponse.data
        setThreadId(threadData.id)

        // Load existing messages
        const threadResponse = await apiClient.getThread(threadData.id)
        if (threadResponse.success && threadResponse.data) {
          setMessages(threadResponse.data.messages || [])
        }
      } else {
        setError(createResponse.error || 'Failed to create thread')
      }
    } catch (err) {
      setError('Failed to load discussion thread')
      console.error('Error loading thread:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const sendMessage = async () => {
    if (!newMessage.trim() || !threadId || isLoading) return

    const messageContent = newMessage.trim()
    setNewMessage('')
    setIsLoading(true)

    try {
      const response = await apiClient.addMessage(threadId, 'user', messageContent)

      if (response.success && response.data) {
        setMessages(prev => [...prev, response.data])

        // Generate AI response with thinking animation
        setIsAiThinking(true)
        setTimeout(async () => {
          try {
            const aiResponse = await generateAiResponse(messageContent, insight!)
            const aiMessageResponse = await apiClient.addMessage(threadId, 'ai', aiResponse)

            if (aiMessageResponse.success && aiMessageResponse.data) {
              setMessages(prev => [...prev, aiMessageResponse.data])
            }
          } catch (err) {
            console.error('Error generating AI response:', err)
          } finally {
            setIsAiThinking(false)
          }
        }, 1000)
      } else {
        setError(response.error || 'Failed to send message')
      }
    } catch (err) {
      setError('Failed to send message')
      console.error('Error sending message:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const parseTimeFromMessage = (message: string): TimeParseResult => {
    const lowerMessage = message.toLowerCase()

    // Parse day of week
    let dayOfWeek: string | undefined
    let timeDescription = 'all time periods'

    const dayNames = {
      'sunday': '0', 'monday': '1', 'tuesday': '2', 'wednesday': '3',
      'thursday': '4', 'friday': '5', 'saturday': '6'
    }

    // Find specific day
    for (const [day, num] of Object.entries(dayNames)) {
      if (lowerMessage.includes(day)) {
        dayOfWeek = num
        timeDescription = day
        break
      }
    }

    // Parse time of day
    let hourStart: number | undefined
    let hourEnd: number | undefined

    if (lowerMessage.includes('morning')) {
      hourStart = 6
      hourEnd = 11
      timeDescription += dayOfWeek ? ' mornings' : 'mornings'
    } else if (lowerMessage.includes('afternoon')) {
      hourStart = 12
      hourEnd = 17
      timeDescription += dayOfWeek ? ' afternoons' : 'afternoons'
    } else if (lowerMessage.includes('evening') || lowerMessage.includes('night')) {
      hourStart = 17
      hourEnd = 21
      timeDescription += dayOfWeek ? ' evenings' : 'evenings'
    } else if (lowerMessage.includes('peak') && lowerMessage.includes('morning')) {
      hourStart = 7
      hourEnd = 9
      timeDescription += dayOfWeek ? ' morning peak' : 'morning peak'
    } else if (lowerMessage.includes('peak') && lowerMessage.includes('evening')) {
      hourStart = 17
      hourEnd = 19
      timeDescription += dayOfWeek ? ' evening peak' : 'evening peak'
    }

    // Handle weekday/weekend
    if (lowerMessage.includes('weekday') && !dayOfWeek) {
      dayOfWeek = '1,2,3,4,5'
      timeDescription = 'weekdays'
    } else if (lowerMessage.includes('weekend') && !dayOfWeek) {
      dayOfWeek = '0,6'
      timeDescription = 'weekends'
    }

    return { dayOfWeek, hourStart, hourEnd, timeDescription }
  }

  const analyzeUserIntent = (userMessage: string, conversationHistory: Message[]): IntentAnalysis => {
    const message = userMessage.toLowerCase()

    // Check for comparative questions - be more aggressive in detection
    const isComparative = message.includes('compare') ||
                         message.includes('vs') ||
                         message.includes('versus') ||
                         message.includes('how does that compare') ||
                         (message.includes('what about') && conversationHistory.length > 0) ||
                         (message.includes('how about') && conversationHistory.length > 0) ||
                         (message.includes('how does') && message.includes('compare')) ||
                         (message.includes('that compare') && conversationHistory.length > 0)

    // Check for follow-up questions about recent data context
    const isFollowUpQuestion = conversationHistory.length > 0 && (
      message.includes('specific zone') ||
      message.includes('which zone') ||
      message.includes('what zone') ||
      message.includes('zone that') ||
      message.includes('stands out') ||
      message.includes('high demand') ||
      message.includes('highest demand') ||
      message.includes('most popular') ||
      message.includes('busiest') ||
      message.includes('top zones') ||
      message.includes('breakdown') ||
      message.includes('during those') ||
      message.includes('during that') ||
      message.includes('show me') ||
      (message.includes('friday') && (message.includes('zone') || message.includes('demand'))) ||
      (message.includes('thursday') && (message.includes('zone') || message.includes('demand')))
    )

    // Determine if this requires real data
    const dataKeywords = ['how many', 'average', 'duration', 'sessions', 'transactions', 'revenue', 'occupancy', 'utilization', 'capacity', 'total', 'stats', 'metrics']
    const requiresData = dataKeywords.some(keyword => message.includes(keyword)) || isComparative || isFollowUpQuestion

    // Determine data type
    let dataType: IntentAnalysis['dataType'] = 'general'
    if (message.includes('duration') || message.includes('time')) dataType = 'duration'
    else if (message.includes('revenue') || message.includes('money') || message.includes('price')) dataType = 'revenue'
    else if (message.includes('occupancy') || message.includes('utilization') || message.includes('capacity') ||
             message.includes('underutilized') || message.includes('overutilized') || message.includes('full') ||
             message.includes('empty') || message.includes('availability')) dataType = 'occupancy'
    else if (message.includes('sessions') || message.includes('transactions') || message.includes('how many')) dataType = 'sessions'

    // For comparative questions, try to infer data type from previous context
    if (isComparative && dataType === 'general' && conversationHistory.length > 0) {
      const recentMessages = conversationHistory.slice(-3).map(m => m.content.toLowerCase()).join(' ')
      if (recentMessages.includes('sessions')) dataType = 'sessions'
      else if (recentMessages.includes('duration')) dataType = 'duration'
      else if (recentMessages.includes('revenue')) dataType = 'revenue'
    }

    // Parse time dynamically instead of using hardcoded filters
    const timeInfo = parseTimeFromMessage(message)

    // Determine zone filter - use insight zone if available
    const zoneMatch = message.match(/z-(\d+)/)
    const zoneFilter = zoneMatch ? zoneMatch[1] : undefined

    // Determine analysis type
    let analysisType: IntentAnalysis['analysisType'] = 'total'
    if (message.includes('average') || message.includes('avg')) analysisType = 'average'
    else if (message.includes('breakdown') || message.includes('by zone') || message.includes('each zone') ||
             message.includes('specific zone') || message.includes('which zone') || message.includes('stands out') ||
             isFollowUpQuestion) analysisType = 'breakdown'
    else if (message.includes('how many') || message.includes('total')) analysisType = 'total'
    else if (isComparative) analysisType = 'comparison'

    // Determine response style
    let responseStyle: IntentAnalysis['responseStyle'] = 'simple'
    if (message.includes('detail') || message.includes('analyze') || message.includes('breakdown')) responseStyle = 'detailed'
    else if (message.includes('trend') || message.includes('pattern') || message.includes('insight')) responseStyle = 'analytical'

    // Determine conversation type
    let conversationType: IntentAnalysis['conversationType'] = 'casual'
    if (requiresData) conversationType = 'data'
    else if (message.includes('recommend') || message.includes('suggest') || message.includes('should')) conversationType = 'guidance'
    else if (message.includes('insight') || message.includes('trend') || message.includes('pattern')) conversationType = 'insight'

    return {
      requiresData,
      dataType,
      timeFilter: undefined, // Legacy - we'll use the parsed time instead
      zoneFilter,
      analysisType,
      responseStyle,
      conversationType,
      timeInfo
    }
  }

  const extractPreviousContext = (conversationHistory: Message[]): TimeParseResult | null => {
    // Look for the last AI response that contains session data with time context
    const recentMessages = conversationHistory.slice(-6) // Look at last 6 messages

    for (let i = recentMessages.length - 1; i >= 0; i--) {
      const message = recentMessages[i]
      if (message.role === 'ai' && message.content.includes('total sessions')) {
        const content = message.content.toLowerCase()

        // Extract day of week from previous context
        const dayNames = {
          'sunday': '0', 'monday': '1', 'tuesday': '2', 'wednesday': '3',
          'thursday': '4', 'friday': '5', 'saturday': '6'
        }

        for (const [day, num] of Object.entries(dayNames)) {
          if (content.includes(day)) {
            let hourStart: number | undefined
            let hourEnd: number | undefined

            // Extract time context
            if (content.includes('morning')) {
              hourStart = 6; hourEnd = 11
            } else if (content.includes('afternoon')) {
              hourStart = 12; hourEnd = 17
            } else if (content.includes('evening') || content.includes('night')) {
              hourStart = 17; hourEnd = 21
            }

            return {
              dayOfWeek: num,
              hourStart,
              hourEnd,
              timeDescription: `${day}${hourStart ? (content.includes('evening') || content.includes('night') ? ' evenings' :
                                                  content.includes('morning') ? ' mornings' :
                                                  content.includes('afternoon') ? ' afternoons' : '') : ''}`
            }
          }
        }
      }
    }

    return null
  }

  const handleComparativeRequest = async (userMessage: string, analysis: IntentAnalysis, conversationHistory: Message[], insight?: Insight): Promise<string> => {
    // Get previous context
    const previousContext = extractPreviousContext(conversationHistory)
    if (!previousContext) {
      return "I need more context for comparison. What specific time period would you like me to compare?"
    }

    // Parse the new time period from the current message
    const newTimeInfo = parseTimeFromMessage(userMessage)

    if (!newTimeInfo.dayOfWeek) {
      return `I can compare with ${previousContext.timeDescription}, but I need you to specify what time period you'd like to compare it to.`
    }

    // Use insight zone if available
    const zoneFilter = insight ? insight.zone_id : analysis.zoneFilter

    // Get data for both time periods
    const [previousData, newData] = await Promise.all([
      apiClient.getSessionCounts(undefined, zoneFilter, previousContext.dayOfWeek, previousContext.hourStart, previousContext.hourEnd),
      apiClient.getSessionCounts(undefined, zoneFilter, newTimeInfo.dayOfWeek, newTimeInfo.hourStart, newTimeInfo.hourEnd)
    ])

    if (!previousData.success || !newData.success || !previousData.data?.data || !newData.data?.data) {
      return "I couldn't retrieve the comparison data. Please try again."
    }

    const prevTotal = previousData.data.data.total_sessions
    const newTotal = newData.data.data.total_sessions
    const difference = newTotal - prevTotal
    const percentChange = prevTotal > 0 ? Math.round((difference / prevTotal) * 100) : 0

    const changeText = difference > 0 ? `${difference} more sessions (+${percentChange}%)` :
                      difference < 0 ? `${Math.abs(difference)} fewer sessions (${percentChange}%)` :
                      'the same number of sessions'

    const zoneText = insight ? ` in zone ${insight.zone_id}` : ''

    return `**Comparison Results${zoneText}:**

${previousContext.timeDescription}: **${prevTotal} sessions**
${newTimeInfo.timeDescription}: **${newTotal} sessions**

${newTimeInfo.timeDescription} had ${changeText} compared to ${previousContext.timeDescription}.`
  }

  const generateAiResponse = async (userMessage: string, insight: Insight): Promise<string> => {
    // AI-first analysis: parse the user's intent and extract parameters
    const analysisResult = analyzeUserIntent(userMessage, messages)

    // If this is a data request, make the appropriate API call
    if (analysisResult.requiresData) {
      try {
        return await handleDataRequest(analysisResult, messages, userMessage, insight)
      } catch (error) {
        console.error('Error in data request:', error)
        return `I'm having trouble accessing the transaction data right now. Let me know what specific information you need and I'll try again.`
      }
    }

    // Handle conversational responses with insight context
    return handleInsightConversationalResponse(userMessage, messages, analysisResult, insight)
  }

  const handleDataRequest = async (analysis: IntentAnalysis, conversationHistory: Message[] = [], userMessage: string = '', insight?: Insight): Promise<string> => {
    const { dataType, zoneFilter, timeInfo, analysisType } = analysis

    // Handle comparative requests specially
    if (analysisType === 'comparison') {
      return handleComparativeRequest(userMessage, analysis, conversationHistory, insight)
    }

    // For follow-up questions, try to extract time context from conversation if not provided in current message
    let dayOfWeek = timeInfo?.dayOfWeek
    let hourStart = timeInfo?.hourStart
    let hourEnd = timeInfo?.hourEnd
    let timeDescription = timeInfo?.timeDescription || 'the requested time period'

    // If this is a follow-up question without explicit time context, use previous context
    if ((!dayOfWeek || !timeDescription || timeDescription === 'all time periods') && conversationHistory.length > 0) {
      const previousContext = extractPreviousContext(conversationHistory)
      if (previousContext) {
        dayOfWeek = previousContext.dayOfWeek
        hourStart = previousContext.hourStart
        hourEnd = previousContext.hourEnd
        timeDescription = previousContext.timeDescription
      }
    }

    // Use insight zone if available
    const effectiveZoneFilter = insight ? insight.zone_id : zoneFilter

    // Make appropriate API call based on analysis
    if (dataType === 'sessions' || dataType === 'general') {
      const response = await apiClient.getSessionCounts(undefined, effectiveZoneFilter, dayOfWeek, hourStart, hourEnd)

      if (response.success && response.data?.data) {
        const data = response.data.data
        const sessions = data.sessions
        const total = data.total_sessions

        return formatSessionResponse(sessions, total, { ...analysis, timeInfo: { ...timeInfo, timeDescription } }, insight, userMessage)
      }
    }

    if (dataType === 'duration') {
      const response = await apiClient.getSessionCounts(undefined, effectiveZoneFilter, dayOfWeek, hourStart, hourEnd)

      if (response.success && response.data?.data) {
        const data = response.data.data
        return formatDurationResponse(data, { ...analysis, timeInfo: { ...timeInfo, timeDescription } })
      }
    }

    if (dataType === 'occupancy') {
      const response = await apiClient.getOccupancyAnalysis()

      if (response.success && response.data?.data) {
        const data = response.data.data
        return formatOccupancyResponse(data, analysis, insight, userMessage)
      }
    }

    return "I couldn't retrieve the requested data. Please try again."
  }

  const formatSessionResponse = (sessions: any[], total: number, analysis: IntentAnalysis, insight?: Insight, userMessage?: string): string => {
    const { analysisType, responseStyle, timeInfo } = analysis

    const timeDescription = timeInfo?.timeDescription || 'the requested time period'
    const zoneText = insight ? ` in zone ${insight.zone_id}` : ' across all zones'

    if (analysisType === 'total' && responseStyle === 'simple') {
      return `**${total} total sessions** during ${timeDescription}${zoneText}.`
    }

    if (analysisType === 'breakdown' || responseStyle === 'detailed') {
      const message = userMessage?.toLowerCase() || ''

      // Check if this is a "highest demand" or "top zones" request
      const isHighestDemandRequest = message.includes('highest demand') ||
                                   message.includes('top zones') ||
                                   message.includes('most popular') ||
                                   message.includes('busiest') ||
                                   (message.includes('show me') && message.includes('demand'))

      // If we have a specific insight zone, show only that zone's data
      if (insight) {
        const zoneSession = sessions.find(s => s.zone === insight.zone_id)
        if (zoneSession) {
          return `Zone ${insight.zone_id} had **${zoneSession.session_count} sessions** during ${timeDescription}.

This represents ${((zoneSession.session_count / total) * 100).toFixed(1)}% of total activity across all zones (${total} total sessions).

Would you like me to compare this with other zones or time periods?`
        }
      }

      if (isHighestDemandRequest) {
        // Show top 5 zones with emphasis on highest demand
        const topZones = sessions.slice(0, 5)
        const topZonesList = topZones.map((s: any, index: number) => {
          const emoji = index === 0 ? '🏆' : index === 1 ? '🥈' : index === 2 ? '🥉' : '•'
          return `${emoji} Zone ${s.zone}: **${s.session_count} sessions** (${((s.session_count/total)*100).toFixed(1)}%)`
        }).join('\n')

        const remainingZones = sessions.length - 5

        return `**Top Demand Zones** during ${timeDescription}:

${topZonesList}${remainingZones > 0 ? `\n...and ${remainingZones} other zones with lower demand` : ''}

Zone ${topZones[0].zone} leads with **${topZones[0].session_count} sessions** (${((topZones[0].session_count/total)*100).toFixed(1)}% of total activity).

Would you like analysis of any specific high-demand zone?`
      }

      // Show breakdown across multiple zones
      const zoneBreakdown = sessions.slice(0, 5).map((s: any) =>
        `• Zone ${s.zone}: ${s.session_count} sessions`
      ).join('\n')

      return `${timeDescription} show **${total} total sessions**:

${zoneBreakdown}${sessions.length > 5 ? `\n...and ${sessions.length - 5} more zones` : ''}

This is historical data from actual transactions. Need more detail on any specific zone or time period?`
    }

    return `${timeDescription} show **${total} total sessions**${zoneText}. Want a breakdown by zone?`
  }

  const formatDurationResponse = (data: any, analysis: IntentAnalysis): string => {
    const { analysisType, timeInfo } = analysis
    const sessions = data.sessions
    const total = data.total_sessions

    const timeDescription = timeInfo?.timeDescription || 'that time period'

    if (analysisType === 'average') {
      // Calculate overall weighted average duration
      const totalMinutes = sessions.reduce((sum: number, s: any) => sum + (s.session_count * s.avg_duration_minutes), 0)
      const totalSessions = sessions.reduce((sum: number, s: any) => sum + s.session_count, 0)
      const overallAvg = totalSessions > 0 ? (totalMinutes / totalSessions) : 0

      const hours = Math.floor(overallAvg / 60)
      const minutes = Math.round(overallAvg % 60)
      const durationText = hours > 0 ? `${hours}h ${minutes}m` : `${minutes} minutes`

      if (sessions.length <= 3) {
        // Simple response for few zones
        return `Average duration on ${timeDescription}: **${durationText}** across ${sessions.length} zones (${total} total sessions).`
      } else {
        // Detailed breakdown for many zones
        const zoneBreakdown = sessions.slice(0, 5).map((s: any) => {
          const zoneHours = Math.floor(s.avg_duration_minutes / 60)
          const zoneMinutes = Math.round(s.avg_duration_minutes % 60)
          const zoneDuration = zoneHours > 0 ? `${zoneHours}h ${zoneMinutes}m` : `${zoneMinutes}m`
          return `• Zone ${s.zone}: ${zoneDuration} avg (${s.session_count} sessions)`
        }).join('\n')

        return `Average duration on ${timeDescription}: **${durationText}** overall

${zoneBreakdown}

This covers ${total} total sessions across ${sessions.length} zones. Need detail on any specific zone?`
      }
    }

    return `Duration data for ${timeDescription} is available. What specific analysis would you like - average duration, breakdown by zone, or duration patterns?`
  }

  const formatOccupancyResponse = (data: any, analysis: IntentAnalysis, insight?: Insight, userMessage?: string): string => {
    const { analysisType } = analysis
    const zones = data.zones
    // const categorized = data.categorized
    const summary = data.summary

    const message = userMessage?.toLowerCase() || ''
    const zoneContext = insight ? ` for ${insight.zone_id}` : ''

    // Filter to specific zone if we have insight context
    let relevantZones = zones
    if (insight && insight.zone_id) {
      relevantZones = zones.filter((z: any) => z.zone === insight.zone_id.replace('z-', ''))
    }

    // Check if this is a "highest occupancy" or "top zones" request
    const isHighestOccupancyRequest = message.includes('highest occupancy') ||
                                     message.includes('top occupancy') ||
                                     message.includes('most utilized') ||
                                     message.includes('busiest zones') ||
                                     (message.includes('show me') && message.includes('occupancy'))

    if (isHighestOccupancyRequest || analysisType === 'breakdown') {
      // Sort zones by occupancy ratio and show top performers
      const zonesWithOccupancy = relevantZones.filter((z: any) => z.avg_daily_occupancy_ratio !== null)
        .sort((a: any, b: any) => (b.avg_daily_occupancy_ratio || 0) - (a.avg_daily_occupancy_ratio || 0))

      if (zonesWithOccupancy.length === 0) {
        return `No capacity data is available yet for occupancy analysis${zoneContext}. The system is working to gather this information.`
      }

      const topZones = zonesWithOccupancy.slice(0, 5)
      const topZonesList = topZones.map((z: any, index: number) => {
        const emoji = index === 0 ? '🏆' : index === 1 ? '🥈' : index === 2 ? '🥉' : '📍'
        const occupancyText = z.avg_daily_occupancy_ratio ? `${z.avg_daily_occupancy_ratio}% occupancy` : 'No data'
        const capacityText = z.capacity ? ` (${z.capacity} spaces)` : ''
        return `${emoji} **${z.location_name || `Zone ${z.zone}`}**: ${occupancyText}${capacityText}`
      }).join('\n')

      const topZone = topZones[0]
      const statusInsight = topZone.avg_daily_occupancy_ratio > 80 ?
        'This suggests high demand and potential capacity constraints.' :
        topZone.avg_daily_occupancy_ratio < 30 ?
        'This indicates underutilization and optimization opportunities.' :
        'This shows healthy utilization levels.'

      if (insight && relevantZones.length === 1) {
        // Zone-specific response
        const zone = relevantZones[0]
        return `**Occupancy Analysis for ${zone.location_name || `Zone ${zone.zone}`}**:

📊 **${zone.avg_daily_occupancy_ratio}% daily occupancy** from ${zone.capacity} total spaces
⏱️ **${zone.avg_utilization_ratio}% time-based utilization**
🎯 **Status**: ${zone.occupancy_status.replace('_', ' ')}

${statusInsight} This zone ${zone.avg_daily_occupancy_ratio > 80 ? 'may benefit from pricing adjustments or capacity expansion' : zone.avg_daily_occupancy_ratio < 30 ? 'presents revenue optimization opportunities' : 'demonstrates effective capacity management'}.

Would you like recommendations for optimizing this zone's performance?`
      }

      return `**Top Occupancy Analysis**${zoneContext}:

${topZonesList}

**${topZone.location_name || `Zone ${topZone.zone}`}** leads with **${topZone.avg_daily_occupancy_ratio}% daily occupancy**. ${statusInsight}

📊 **Summary**: ${summary.high_demand_zones} high-demand, ${summary.optimal_zones} optimal, ${summary.underutilized_zones} underutilized zones.

Would you like detailed analysis of any specific zone's capacity management?`
    }

    // General occupancy overview
    const totalZonesWithData = summary.zones_with_capacity_data
    const highDemandCount = summary.high_demand_zones
    const underutilizedCount = summary.underutilized_zones
    const optimalCount = summary.optimal_zones

    return `**Occupancy Analysis Overview**${zoneContext}:

📊 **${totalZonesWithData} zones** have capacity data available:
• 🔥 **${highDemandCount} high-demand zones** (>80% occupancy)
• ✅ **${optimalCount} optimal zones** (50-80% occupancy)
• 📉 **${underutilizedCount} underutilized zones** (<30% occupancy)

${highDemandCount > 0 ? `High-demand zones may benefit from pricing adjustments or capacity expansion. ` : ''}${underutilizedCount > 0 ? `Underutilized zones present revenue optimization opportunities.` : ''}

Ask about "highest occupancy zones" or "underutilized zones" for detailed breakdowns.`
  }

  const handleInsightConversationalResponse = (userMessage: string, conversationHistory: Message[], analysis: IntentAnalysis, insight: Insight): string => {
    const message = userMessage.toLowerCase()

    // Handle based on conversation type
    if (analysis.conversationType === 'guidance') {
      return handleGuidanceRequest(message, insight)
    }

    if (analysis.conversationType === 'insight') {
      return handleInsightRequest(message, insight)
    }

    // General conversational responses with insight context
    return handleGeneralInsightConversation(message, conversationHistory, insight)
  }

  const handleGuidanceRequest = (message: string, insight: Insight): string => {
    if (message.includes('recommend') || message.includes('suggest')) {
      return `Based on the ${insight.kind || 'general'} insight for zone ${insight.zone_id}, I can provide targeted recommendations:

**Strategic Recommendations:**
• **Occupancy Optimization**: Analyze current utilization patterns
• **Revenue Enhancement**: Dynamic pricing based on demand patterns
• **Operational Efficiency**: Streamline processes for peak periods
• **Customer Experience**: Improve service delivery during high-demand times

${insight.confidence && insight.confidence > 0.7 ? 'This insight has high confidence, making it ideal for immediate action.' : 'Consider gathering more data to strengthen the recommendation basis.'}

What specific area would you like me to focus on?`
    }

    return `I can help with strategic analysis for zone ${insight.zone_id}. What specific guidance are you looking for?`
  }

  const handleInsightRequest = (_message: string, insight: Insight): string => {
    return `For zone ${insight.zone_id}, I can analyze trends and patterns:

**Current Insight Analysis:**
• Type: ${insight.kind || 'General optimization opportunity'}
• Confidence: ${insight.confidence ? `${Math.round(insight.confidence * 100)}%` : 'Under review'}
• Zone Focus: ${insight.zone_id}

${insight.narrative_text ? `**Details**: ${insight.narrative_text}` : ''}

Would you like me to dive deeper into any specific trend pattern or compare with other zones?`
  }

  const handleGeneralInsightConversation = (message: string, conversationHistory: Message[], insight: Insight): string => {
    if (message.includes('hello') || message.includes('hi') || conversationHistory.length === 0) {
      return `Hello! I'm here to help with zone ${insight.zone_id} analysis. This ${insight.kind || 'insight'} suggests optimization opportunities.

**I can help with:**
• **Performance Analysis**: Compare this zone with others or across time periods
• **Optimization Strategies**: Recommend specific improvements
• **Data Insights**: Deep-dive into transaction patterns and trends

What would you like to explore about zone ${insight.zone_id}?`
    }

    return `I understand you're asking about "${message}" for zone ${insight.zone_id}. I can help with performance analysis, strategic planning, and data insights for this zone.

What specific aspect would you like me to focus on?`
  }


  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatMessageTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-end">
      <div className="bg-white w-96 h-full shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Discuss Insight</h3>
            {insight && (
              <p className="text-sm text-gray-500">Zone: {insight.zone_id}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading && messages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-level-blue mx-auto mb-2"></div>
              <p>Loading discussion...</p>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-level-blue text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="flex items-center space-x-2 mb-1">
                      {message.role === 'user' ? (
                        <User className="w-3 h-3" />
                      ) : (
                        <Bot className="w-3 h-3" />
                      )}
                      <span className="text-xs opacity-75">
                        {message.role === 'user' ? 'You' : 'Analyst'}
                      </span>
                      <span className="text-xs opacity-75">
                        {formatMessageTime(message.created_at)}
                      </span>
                    </div>
                    <p className="text-sm">{message.content}</p>
                  </div>
                </div>
              ))}

              {/* AI Thinking Animation */}
              {isAiThinking && (
                <div className="flex justify-start">
                  <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-gray-100 text-gray-900">
                    <div className="flex items-center space-x-2 mb-1">
                      <Bot className="w-3 h-3" />
                      <span className="text-xs opacity-75">Analyst</span>
                      <span className="text-xs opacity-75">thinking...</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                      <span className="text-xs text-gray-500 ml-2">Generating response...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Auto-scroll target */}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about this insight or request recommendations..."
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-level-blue focus:border-transparent"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!newMessage.trim() || isLoading}
              className="bg-level-blue text-white px-4 py-2 rounded-lg hover:bg-level-blue/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}