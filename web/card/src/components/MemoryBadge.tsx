import { Brain, AlertTriangle, Info } from 'lucide-react'

interface MemoryBadgeProps {
  kind: 'canonical' | 'context' | 'exception'
  count: number
  onClick?: () => void
}

export default function MemoryBadge({ kind, count, onClick }: MemoryBadgeProps) {
  const getKindConfig = (kind: string) => {
    switch (kind) {
      case 'canonical':
        return {
          icon: Brain,
          color: 'bg-level-blue text-white',
          label: 'Rules'
        }
      case 'exception':
        return {
          icon: AlertTriangle,
          color: 'bg-level-amber text-white',
          label: 'Exceptions'
        }
      case 'context':
      default:
        return {
          icon: Info,
          color: 'bg-level-green text-white',
          label: 'Context'
        }
    }
  }

  const config = getKindConfig(kind)
  const Icon = config.icon

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${config.color} hover:opacity-90 transition-opacity`}
    >
      <Icon className="w-3 h-3" />
      <span>{config.label}</span>
      {count > 0 && (
        <span className="bg-white bg-opacity-20 rounded-full px-1.5 py-0.5 text-xs">
          {count}
        </span>
      )}
    </button>
  )
}