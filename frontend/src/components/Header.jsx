import { Menu } from 'lucide-react'
import { useLocation } from 'react-router-dom'

const pageTitles = {
  '/': ['Command overview', 'Flood coordination'],
  '/map': ['Live risk map', 'Zone intelligence'],
  '/simulation': ['Flood simulation', 'Scenario planning'],
  '/reports': ['Citizen reports', 'Community signals'],
  '/resources': ['Resource status', 'Response inventory'],
  '/analytics': ['Analytics', 'Impact indicators'],
}

export default function Header({ apiStatus, onMenuClick }) {
  const { pathname } = useLocation()
  const [title, section] = pageTitles[pathname] || pageTitles['/']
  const dateLabel = new Intl.DateTimeFormat('en', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(new Date())
  return (
    <header className="topbar">
      <button className="icon-button mobile-menu" type="button" aria-label="Open navigation" title="Open navigation" onClick={onMenuClick}><Menu size={21} /></button>
      <div className="topbar-title"><span className="topbar-section">{section}</span><h1>{title}</h1></div>
      <div className="topbar-meta">
        <span className="demo-tag"><span /> DEMO DATA</span>
        <span className={`api-status api-${apiStatus}`}><span className="status-dot" />{apiStatus === 'connected' ? 'API CONNECTED' : apiStatus === 'offline' ? 'API OFFLINE' : 'CHECKING API'}</span>
        <span className="topbar-date">{dateLabel}</span>
      </div>
    </header>
  )
}