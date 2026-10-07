import { Activity, BarChart3, ClipboardList, CloudRain, LayoutDashboard, Map, Package, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/map', label: 'Risk map', icon: Map },
  { to: '/simulation', label: 'Flood simulation', icon: CloudRain },
  { to: '/reports', label: 'Citizen reports', icon: ClipboardList },
  { to: '/resources', label: 'Resources', icon: Package },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export default function Sidebar({ open, onNavigate }) {
  return (
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`} aria-label="Main navigation">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true"><Activity size={21} strokeWidth={2.4} /></div>
        <div className="brand-copy"><span className="brand-name">LIFEGRID</span><span className="brand-caption">EARLY ACTION NETWORK</span></div>
        <button className="icon-button sidebar-close" type="button" title="Close navigation" aria-label="Close navigation" onClick={onNavigate}><X size={19} /></button>
      </div>
      <div className="sidebar-section-label">OPERATIONS</div>
      <nav className="sidebar-nav">
        {navigation.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} onClick={onNavigate} className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
            <Icon size={18} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-lower">
        <div className="sidebar-section-label">CURRENT SCENARIO</div>
        <div className="scenario-chip"><span className="scenario-pulse" /><span>URBAN FLOOD</span><span className="scenario-tag">DEMO</span></div>
        <div className="sidebar-footnote">Synthetic response data<br />Local environment</div>
      </div>
    </aside>
  )
}