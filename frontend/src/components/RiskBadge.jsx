const labels = { LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High', CRITICAL: 'Critical' }

export default function RiskBadge({ level, compact = false }) {
  const normalized = labels[level] ? level.toLowerCase() : 'unknown'
  return <span className={`risk-badge risk-${normalized} ${compact ? 'risk-badge-compact' : ''}`}><span className="risk-indicator" />{labels[level] || 'Unavailable'}</span>
}