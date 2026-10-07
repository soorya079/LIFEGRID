import { AlertTriangle, LoaderCircle, RefreshCw } from 'lucide-react'

export function LoadingState({ label = 'Loading local response data' }) {
  return <div className="loading-state" role="status"><LoaderCircle className="loading-spinner" size={21} /><span>{label}</span></div>
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="error-state" role="alert">
      <span className="error-icon"><AlertTriangle size={19} /></span>
      <div className="error-copy"><strong>{error?.status ? `API ${error.status}` : 'API unavailable'}</strong><p>{error?.message || 'The request could not be completed.'}</p>
        {error?.details?.length > 0 && <ul>{error.details.slice(0, 4).map((item, index) => <li key={`${item.location}-${index}`}>{item.location}: {item.message}</li>)}</ul>}
      </div>
      {onRetry && <button className="button button-secondary error-retry" type="button" onClick={onRetry}><RefreshCw size={15} /> Retry</button>}
    </div>
  )
}

export default function LoadingStateWrapper({ loading, error, onRetry, children }) {
  if (loading) return <LoadingState />
  if (error) return <ErrorState error={error} onRetry={onRetry} />
  return children
}