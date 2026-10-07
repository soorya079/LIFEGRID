export default function StatCard({ label, value, detail, icon: Icon, tone = 'neutral', demo = false }) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <div className="stat-topline"><span className="stat-label">{label}</span><span className="stat-icon" aria-hidden="true"><Icon size={18} strokeWidth={1.8} /></span></div>
      <div className="stat-value-row"><strong className="stat-value">{value}</strong>{demo && <span className="mini-demo-tag">DEMO</span>}</div>
      <p className="stat-detail">{detail}</p>
    </article>
  )
}