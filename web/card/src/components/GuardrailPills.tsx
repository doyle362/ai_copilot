import { Shield, AlertCircle, CheckCircle } from 'lucide-react'

interface GuardrailPillsProps {
  guardrails?: Array<{
    name: string
    status: 'pass' | 'warn' | 'fail'
    message?: string
  }>
}

export default function GuardrailPills({ guardrails = [] }: GuardrailPillsProps) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'pass':
        return {
          icon: CheckCircle,
          color: 'bg-level-green text-white',
        }
      case 'warn':
        return {
          icon: AlertCircle,
          color: 'bg-level-amber text-white',
        }
      case 'fail':
        return {
          icon: AlertCircle,
          color: 'bg-level-red text-white',
        }
      default:
        return {
          icon: Shield,
          color: 'bg-gray-500 text-white',
        }
    }
  }

  if (guardrails.length === 0) {
    return (
      <div className="flex items-center space-x-2">
        <Shield className="w-4 h-4 text-gray-400" />
        <span className="text-sm text-gray-500">No guardrails configured</span>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {guardrails.map((guardrail, index) => {
        const config = getStatusConfig(guardrail.status)
        const Icon = config.icon

        return (
          <div
            key={index}
            className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${config.color}`}
            title={guardrail.message || guardrail.name}
          >
            <Icon className="w-3 h-3" />
            <span>{guardrail.name}</span>
          </div>
        )
      })}
    </div>
  )
}