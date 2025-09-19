import { useState, useEffect, useRef } from 'react'
import { X, Send, User, Bot, AlertCircle, Trash2 } from 'lucide-react'
import { apiClient } from '../api'

interface GeneralChatDrawerProps {
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
  dataType: 'sessions' | 'duration' | 'revenue' | 'occupancy' | 'kpi' | 'general'
  timeFilter?: string
  zoneFilter?: string
  analysisType: 'count' | 'average' | 'breakdown' | 'total' | 'comparison'
  responseStyle: 'simple' | 'detailed' | 'analytical'
  conversationType: 'data' | 'guidance' | 'insight' | 'casual'
  timeInfo?: TimeParseResult
}

export default function GeneralChatDrawer({ isOpen, onClose }: GeneralChatDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isAiThinking, setIsAiThinking] = useState(false)
  const [threadId, setThreadId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      loadOrCreateGeneralThread()
    } else {
      // Reset state when drawer closes
      setMessages([])
      setThreadId(null)
      setNewMessage('')
      setError(null)
      setIsAiThinking(false)
    }
  }, [isOpen])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isAiThinking])

  const loadOrCreateGeneralThread = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Create a general thread (not tied to any specific insight)
      const createResponse = await apiClient.createThread(null, null, 'general')

      if (createResponse.success && createResponse.data) {
        const threadData = createResponse.data
        setThreadId(threadData.id)

        // Load existing messages
        const threadResponse = await apiClient.getThread(threadData.id)
        if (threadResponse.success && threadResponse.data) {
          setMessages(threadResponse.data.messages || [])
        }
      } else {
        setError(createResponse.error || 'Failed to create general chat')
      }
    } catch (err) {
      setError('Failed to load general chat')
      console.error('Error loading general chat:', err)
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
    if (message.includes('kpi') || message.includes('metric') || message.includes('benchmark') ||
        message.includes('industry standard') || message.includes('best practice') ||
        message.includes('how to calculate') || message.includes('formula') ||
        message.includes('revpash') || message.includes('efficiency ratio') ||
        message.includes('what is') && (message.includes('occupancy') || message.includes('revenue') || message.includes('utilization'))) {
      dataType = 'kpi'
    }
    else if (message.includes('duration') || message.includes('time')) dataType = 'duration'
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

    // Determine zone filter
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

    const result = {
      requiresData,
      dataType,
      timeFilter: undefined, // Legacy - we'll use the parsed time instead
      zoneFilter,
      analysisType,
      responseStyle,
      conversationType,
      timeInfo
    }


    return result
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

  const handleComparativeRequest = async (userMessage: string, analysis: IntentAnalysis, conversationHistory: Message[]): Promise<string> => {
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

    // Get data for both time periods
    const [previousData, newData] = await Promise.all([
      apiClient.getSessionCounts(undefined, analysis.zoneFilter, previousContext.dayOfWeek, previousContext.hourStart, previousContext.hourEnd),
      apiClient.getSessionCounts(undefined, analysis.zoneFilter, newTimeInfo.dayOfWeek, newTimeInfo.hourStart, newTimeInfo.hourEnd)
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

    return `**Comparison Results:**

${previousContext.timeDescription}: **${prevTotal} sessions**
${newTimeInfo.timeDescription}: **${newTotal} sessions**

${newTimeInfo.timeDescription} had ${changeText} compared to ${previousContext.timeDescription}.`
  }

  const handleDataRequest = async (analysis: IntentAnalysis, conversationHistory: Message[] = [], userMessage: string = ''): Promise<string> => {
    const { dataType, zoneFilter, timeInfo, analysisType } = analysis

    // Handle comparative requests specially
    if (analysisType === 'comparison') {
      return handleComparativeRequest(userMessage, analysis, conversationHistory)
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

    // Make appropriate API call based on analysis
    if (dataType === 'sessions' || dataType === 'general') {
      const response = await apiClient.getSessionCounts(undefined, zoneFilter, dayOfWeek, hourStart, hourEnd)

      if (response.success && response.data?.data) {
        const data = response.data.data
        const sessions = data.sessions
        const total = data.total_sessions

        return formatSessionResponse(sessions, total, { ...analysis, timeInfo: { ...timeInfo, timeDescription } }, userMessage)
      }
    }

    if (dataType === 'duration') {
      const response = await apiClient.getSessionCounts(undefined, zoneFilter, dayOfWeek, hourStart, hourEnd)

      if (response.success && response.data?.data) {
        const data = response.data.data
        return formatDurationResponse(data, analysis)
      }
    }

    if (dataType === 'occupancy') {
      const response = await apiClient.getOccupancyAnalysis()

      if (response.success && response.data?.data) {
        const data = response.data.data
        return formatOccupancyResponse(data, analysis, userMessage)
      }
    }

    if (dataType === 'kpi') {
      return await handleKpiRequest(userMessage, analysis)
    }

    return "I couldn't retrieve the requested data. Please try again."
  }

  const handleKpiRequest = async (userMessage: string, _analysis: IntentAnalysis): Promise<string> => {
    const message = userMessage.toLowerCase()

    // Extract context keywords from the user's message
    const contextKeywords: string[] = []

    // Add context based on the question type
    if (message.includes('occupancy') || message.includes('utilization') || message.includes('capacity')) {
      contextKeywords.push('occupancy', 'efficiency', 'utilization')
    }
    if (message.includes('revenue') || message.includes('money') || message.includes('price') || message.includes('revpash')) {
      contextKeywords.push('revenue', 'performance')
    }
    if (message.includes('duration') || message.includes('time') || message.includes('session')) {
      contextKeywords.push('duration', 'turnover')
    }
    if (message.includes('benchmark') || message.includes('standard')) {
      contextKeywords.push('benchmark')
    }
    if (message.includes('best practice') || message.includes('recommendation')) {
      contextKeywords.push('best_practice')
    }

    // If no specific context, add general parking terms
    if (contextKeywords.length === 0) {
      contextKeywords.push('parking', 'general')
    }

    try {
      // Get KPI knowledge
      const kpiResponse = await apiClient.getKpiKnowledge(contextKeywords.join(','))

      // Get analytical patterns for additional context
      const patternsResponse = await apiClient.getAnalyticalPatterns(contextKeywords.join(','))

      // Get industry knowledge for best practices
      const industryResponse = await apiClient.getIndustryKnowledge(contextKeywords.join(','))

      let response = ""

      // Handle specific KPI questions
      if (message.includes('revpash') || (message.includes('revenue') && message.includes('space'))) {
        const revpashKpi = kpiResponse.data?.data?.kpis?.find((kpi: any) =>
          kpi.kpi_name.toLowerCase().includes('revpash') || kpi.kpi_name.toLowerCase().includes('revenue per available space')
        )

        if (revpashKpi) {
          response = `**Revenue Per Available Space Hour (RevPASH)**\n\n`
          response += `📊 **Formula**: ${revpashKpi.calculation_formula}\n\n`

          if (revpashKpi.interpretation_rules) {
            const rules = typeof revpashKpi.interpretation_rules === 'string'
              ? JSON.parse(revpashKpi.interpretation_rules)
              : revpashKpi.interpretation_rules

            response += `**Performance Thresholds**:\n`
            Object.entries(rules).forEach(([level, rule]: [string, any]) => {
              const emoji = level === 'excellent' ? '🟢' : level === 'good' ? '🟡' : level === 'concerning' ? '🟠' : '🔴'
              response += `${emoji} **${level.charAt(0).toUpperCase() + level.slice(1)}**: ${rule.meaning}\n`
            })
          }

          if (revpashKpi.industry_benchmarks) {
            const benchmarks = typeof revpashKpi.industry_benchmarks === 'string'
              ? JSON.parse(revpashKpi.industry_benchmarks)
              : revpashKpi.industry_benchmarks

            response += `\n**Industry Benchmarks**:\n`
            Object.entries(benchmarks).forEach(([type, benchmark]: [string, any]) => {
              response += `• **${type.charAt(0).toUpperCase() + type.slice(1)}**: ${benchmark.target || benchmark.average || 'N/A'}\n`
            })
          }
        }
      }
      else if (message.includes('occupancy efficiency') || message.includes('efficiency ratio')) {
        const occupancyKpi = kpiResponse.data?.data?.kpis?.find((kpi: any) =>
          kpi.kpi_name.toLowerCase().includes('occupancy efficiency')
        )

        if (occupancyKpi) {
          response = `**Occupancy Efficiency Ratio**\n\n`
          response += `📊 **Formula**: ${occupancyKpi.calculation_formula}\n\n`

          if (occupancyKpi.interpretation_rules) {
            const rules = typeof occupancyKpi.interpretation_rules === 'string'
              ? JSON.parse(occupancyKpi.interpretation_rules)
              : occupancyKpi.interpretation_rules

            response += `**Performance Levels**:\n`
            Object.entries(rules).forEach(([level, rule]: [string, any]) => {
              const emoji = level === 'excellent' ? '🟢' : level === 'good' ? '🟡' : level === 'concerning' ? '🟠' : '🔴'
              const range = rule.min && rule.max ? `${rule.min}-${rule.max}%` :
                           rule.min ? `${rule.min}%+` :
                           rule.max ? `<${rule.max}%` : ''
              response += `${emoji} **${level.charAt(0).toUpperCase() + level.slice(1)}** (${range}): ${rule.meaning}\n`
            })
          }
        }
      }
      else {
        // General KPI overview
        if (kpiResponse.data?.data?.kpis?.length > 0) {
          response = `**Key Performance Indicators for Parking Analytics**\n\n`

          const kpis = kpiResponse.data.data.kpis.slice(0, 3) // Show top 3 relevant KPIs
          kpis.forEach((kpi: any, index: number) => {
            response += `**${index + 1}. ${kpi.kpi_name}** (${kpi.kpi_category})\n`
            response += `📊 Formula: ${kpi.calculation_formula}\n`

            if (kpi.interpretation_rules) {
              try {
                const rules = typeof kpi.interpretation_rules === 'string'
                  ? JSON.parse(kpi.interpretation_rules)
                  : kpi.interpretation_rules
                const ruleKeys = Object.keys(rules)
                if (ruleKeys.length > 0) {
                  const firstRule = rules[ruleKeys[0]]
                  response += `💡 Focus: ${firstRule.meaning || 'Performance measurement'}\n`
                }
              } catch (e) {
                // Skip if JSON parsing fails
              }
            }
            response += '\n'
          })
        }
      }

      // Add industry knowledge if available
      if (industryResponse.data?.data?.knowledge?.length > 0) {
        const knowledge = industryResponse.data.data.knowledge[0] // Most relevant
        response += `\n**Industry Insight**: ${knowledge.content}\n`
      }

      // Add analytical patterns if available
      if (patternsResponse.data?.data?.patterns?.length > 0) {
        const pattern = patternsResponse.data.data.patterns[0] // Most relevant
        if (pattern.example_insights && pattern.example_insights.length > 0) {
          response += `\n**Analysis Pattern**: ${pattern.example_insights[0]}\n`
        }
      }

      // Add helpful follow-up suggestions
      response += `\n💡 **Ask me about**:\n`
      response += `• "Show me RevPASH calculation" for revenue metrics\n`
      response += `• "What's a good occupancy ratio?" for capacity insights\n`
      response += `• "Industry benchmarks for downtown parking" for comparisons\n`

      return response || "I found relevant KPI information but couldn't format it properly. Please try asking about a specific metric like RevPASH or occupancy efficiency."

    } catch (error) {
      console.error('Error fetching KPI knowledge:', error)
      return "I couldn't retrieve KPI information right now. Please try again or ask about specific metrics like occupancy efficiency or RevPASH."
    }
  }

  const formatSessionResponse = (sessions: any[], total: number, analysis: IntentAnalysis, userMessage?: string): string => {
    const { analysisType, responseStyle, timeInfo } = analysis

    const timeDescription = timeInfo?.timeDescription || 'all time periods'

    if (analysisType === 'total' && responseStyle === 'simple') {
      return `**${total} total sessions** during ${timeDescription} across all zones.`
    }

    if (analysisType === 'breakdown' || responseStyle === 'detailed') {
      const message = userMessage?.toLowerCase() || ''

      // Check if this is a "highest demand" or "top zones" request
      const isHighestDemandRequest = message.includes('highest demand') ||
                                   message.includes('top zones') ||
                                   message.includes('most popular') ||
                                   message.includes('busiest') ||
                                   (message.includes('show me') && message.includes('demand'))

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

      // Standard breakdown format
      const zoneBreakdown = sessions.map((s: any) =>
        `• Zone ${s.zone}: ${s.session_count} sessions`
      ).join('\n')

      return `${timeDescription} see **${total} total sessions** across all zones:

${zoneBreakdown}

This is historical data from actual transactions. Need more detail on any specific zone or time period?`
    }

    return `${timeDescription} show **${total} total sessions** across ${sessions.length} zones. Want a breakdown by zone?`
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
          return `• z-${s.zone}: ${zoneDuration} avg (${s.session_count} sessions)`
        }).join('\n')

        return `Average duration on ${timeDescription}: **${durationText}** overall

${zoneBreakdown}

This covers ${total} total sessions across ${sessions.length} zones. Need detail on any specific zone?`
      }
    }

    return `Duration data for ${timeDescription} is available. What specific analysis would you like - average duration, breakdown by zone, or duration patterns?`
  }

  const formatOccupancyResponse = (data: any, analysis: IntentAnalysis, userMessage?: string): string => {
    const { analysisType } = analysis
    const zones = data.zones
    // const categorized = data.categorized
    const summary = data.summary

    const message = userMessage?.toLowerCase() || ''

    // Check if this is a "highest occupancy" or "top zones" request
    const isHighestOccupancyRequest = message.includes('highest occupancy') ||
                                     message.includes('top occupancy') ||
                                     message.includes('most utilized') ||
                                     message.includes('busiest zones') ||
                                     (message.includes('show me') && message.includes('occupancy'))

    if (isHighestOccupancyRequest || analysisType === 'breakdown') {
      // Sort zones by occupancy ratio and show top performers
      const zonesWithOccupancy = zones.filter((z: any) => z.avg_daily_occupancy_ratio !== null)
        .sort((a: any, b: any) => (b.avg_daily_occupancy_ratio || 0) - (a.avg_daily_occupancy_ratio || 0))

      if (zonesWithOccupancy.length === 0) {
        return `No capacity data is available yet for occupancy analysis. The system is working to gather this information.`
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

      return `**Top Occupancy Analysis** across all zones:

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

    return `**Occupancy Analysis Overview**:

📊 **${totalZonesWithData} zones** have capacity data available:
• 🔥 **${highDemandCount} high-demand zones** (>80% occupancy)
• ✅ **${optimalCount} optimal zones** (50-80% occupancy)
• 📉 **${underutilizedCount} underutilized zones** (<30% occupancy)

${highDemandCount > 0 ? `High-demand zones may benefit from pricing adjustments or capacity expansion. ` : ''}${underutilizedCount > 0 ? `Underutilized zones present revenue optimization opportunities.` : ''}

Ask about "highest occupancy zones" or "underutilized zones" for detailed breakdowns.`
  }

  const handleConversationalResponse = (userMessage: string, conversationHistory: Message[], analysis: IntentAnalysis): string => {
    const message = userMessage.toLowerCase()

    // Handle based on conversation type
    if (analysis.conversationType === 'guidance') {
      return handleGuidanceRequest(message)
    }

    if (analysis.conversationType === 'insight') {
      return handleInsightRequest(message)
    }

    // Context-aware responses for follow-up questions
    const recentMessages = conversationHistory.slice(-3)
    const recentContent = recentMessages.map(m => m.content.toLowerCase()).join(' ')

    if (recentContent.includes('friday evening') || recentContent.includes('3513 total sessions')) {
      return handleFridayContextQuestions(message)
    }

    // General conversational responses
    return handleGeneralConversation(message, conversationHistory)
  }

  const handleGuidanceRequest = (message: string): string => {
    if (message.includes('look for') || message.includes('focus on')) {
      return `As your parking analyst, I recommend focusing on these key insight types:

**High-Priority Patterns to Watch:**
• **Occupancy Efficiency**: Zones with <80% or >95% occupancy need attention
• **Revenue Optimization**: Price points that aren't maximizing revenue per space
• **Seasonal Adjustments**: Quarterly demand pattern changes
• **Multi-day Patterns**: Extended stay opportunities (especially in residential zones)

What type of insights are you most interested in tracking?`
    }

    return `I can help with strategic analysis across your zones. What specific guidance are you looking for?`
  }

  const handleInsightRequest = (_message: string): string => {
    return `I can analyze trends and patterns across all your zones. Based on current data patterns:

**Cross-Zone Trends:**
• Seasonal demand variations affecting multiple zones
• Weekend vs weekday pricing opportunities
• Multi-day stay patterns emerging in residential areas

Would you like me to dive deeper into any specific trend pattern?`
  }

  const handleFridayContextQuestions = (message: string): string => {
    if (message.includes('time frame') || message.includes('timeframe') || message.includes('hours')) {
      return `For the Friday evening analysis, I looked at **Friday evenings between 5 PM and 9 PM** (17:00-21:00). This is a common peak period for parking activity.

Would you like me to analyze a different time period, or break this down by specific hours?`
    }

    if (message.includes('days') || message.includes('date range')) {
      return `The Friday evening analysis covers **all historical data** in the database - every Friday evening (5-9 PM) transaction from all available records.

Would you like me to break this down by specific date ranges or analyze trends over time?`
    }

    return `Based on our Friday evening discussion, what specific aspect would you like me to explore further?`
  }

  const handleGeneralConversation = (message: string, conversationHistory: Message[]): string => {
    if (message.includes('hello') || message.includes('hi') || conversationHistory.length === 0) {
      return `Hello! I'm your Level Analyst AI assistant. I have access to all your zone data and can help with:

**Zone Analysis**: Performance trends, occupancy patterns, revenue optimization
**Strategic Planning**: Multi-zone coordination, seasonal adjustments, pricing strategies
**Data Insights**: Real-time analytics from your transaction database

What would you like to explore today?`
    }

    return `I understand you're asking about "${message}". I can help with zone analysis, strategic planning, and data insights from your transaction database.

What specific aspect would you like me to focus on?`
  }

  const generateGeneralAiResponse = async (userMessage: string, conversationHistory: Message[]): Promise<string> => {
    // AI-first analysis: parse the user's intent and extract parameters
    const analysisResult = analyzeUserIntent(userMessage, conversationHistory)

    // If this is a data request, make the appropriate API call
    if (analysisResult.requiresData) {
      try {
        return await handleDataRequest(analysisResult, conversationHistory, userMessage)
      } catch (error) {
        console.error('Error in data request:', error)
        return `I'm having trouble accessing the transaction data right now. Let me know what specific information you need and I'll try again.`
      }
    }

    // Handle conversational responses
    return handleConversationalResponse(userMessage, conversationHistory, analysisResult)
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
            const aiResponse = await generateGeneralAiResponse(messageContent, messages)
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChatHistory = async () => {
    if (!threadId) return

    try {
      // Create a new thread to replace the current one
      const response = await apiClient.createThread(null, null, 'general')

      if (response.success && response.data) {
        setThreadId(response.data.id)
        setMessages([])
        setError(null)
      }
    } catch (error) {
      console.error('Error clearing chat history:', error)
      setError('Failed to clear chat history')
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
            <h3 className="text-lg font-semibold text-gray-900">Analyst Chat</h3>
            <p className="text-sm text-gray-500">General discussion & strategy</p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={clearChatHistory}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="Clear chat history"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="Close chat"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
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
              <p>Loading chat...</p>
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
                      <span className="text-xs text-gray-500 ml-2">Analyzing...</span>
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
              placeholder="Ask about trends, zones, insights, or strategy..."
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
