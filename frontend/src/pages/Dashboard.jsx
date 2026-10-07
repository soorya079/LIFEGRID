import { useEffect, useState } from 'react'
import { Activity, ArrowUpRight, BedDouble, Droplet, ShieldAlert, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getReports, getResourceSummary, getZoneAssessments } from '../api/client'
import LoadingState, { ErrorState } from '../components/LoadingState'
import RiskChart from '../components/RiskChart'
import StatCard from '../components/StatCard'
import ZoneTable from '../components/ZoneTable'

const formatNumber = new Intl.NumberFormat('en')
const riskLevels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

function summarize(zones) {
  const distribution = Object.fromEntries(riskLevels.map((level) => [level, 0]))
  let totalPopulation = 0
  let affectedPopulation = 0
  let shelterCapacity = 0
  for (const zone of zones) {
    distribution[zone.risk.risk_level] += 1
    totalPopulation += zone.population
    affectedPopulation += zone.simulation.affected_population
    shelterCapacity += zone.population * zone.shelter_capacity
  }
  const highestRisk = [...zones].sort((left, right) => right.risk.risk_score - left.risk.risk_score)[0]
  return { distribution, totalPopulation, affectedPopulation, shelterCapacity: totalPopulation ? Math.round(shelterCapacity / totalPopulation) : 0, highestRisk }
}

export default function Dashboard() {
  const [zones, setZones] = useState([])
  const [dataLabel, setDataLabel] = useState('')
  const [activeIncidents, setActiveIncidents] = useState(0)
  const [shortageTypes, setShortageTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reload, setReload] = useState(0)
  const refresh = () => {
    setLoading(true)
    setError(null)
    setReload((value) => value + 1)
  }

  useEffect(() => {
    let active = true
    Promise.all([getZoneAssessments(), getReports(), getResourceSummary()]).then(([result, reportsResponse, resourceSummary]) => {
      if (active) {
        setZones(result.zones)
        setDataLabel(result.dataLabel)
        setActiveIncidents(reportsResponse.reports.filter((report) => !['RESOLVED', 'REJECTED'].includes(report.status)).length)
        setShortageTypes(resourceSummary.resources.filter((item) => item.shortage > 0).map((item) => item.type))
      }
    }).catch((requestError) => active && setError(requestError)).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [reload])

  if (loading) return <LoadingState label="Assessing synthetic flood zones" />
  if (error) return <ErrorState error={error} onRetry={refresh} />

  const summary = summarize(zones)
  const highestRiskLevel = summary.highestRisk?.risk.risk_level || 'LOW'
  return (
    <div className="page-stack page-enter">
      <section className="page-intro"><div><p className="eyebrow">URBAN FLOOD · COMMAND VIEW</p><h2>Situation overview</h2><p className="intro-copy">A zone-by-zone picture from the local deterministic risk engine.</p></div>
        <div className="intro-actions"><span className="data-source-tag">{dataLabel}</span><button className="button button-secondary" type="button" onClick={refresh}><Activity size={16} /> Refresh assessment</button></div>
      </section>
      <section className="stat-grid" aria-label="Situation metrics">
        <StatCard label="RISK STATUS" value={highestRiskLevel} detail={summary.highestRisk ? `Highest zone: ${summary.highestRisk.name}` : 'No zone assessments'} icon={ShieldAlert} tone={highestRiskLevel.toLowerCase()} />
        <StatCard label="AFFECTED POPULATION" value={formatNumber.format(summary.affectedPopulation)} detail={`Estimated across ${zones.length} synthetic zones`} icon={Users} />
        <StatCard label="ACTIVE INCIDENTS" value={formatNumber.format(activeIncidents)} detail="Stored reports awaiting resolution" icon={Activity} tone="amber" />
        <StatCard label="SHELTER ADEQUACY" value={`${summary.shelterCapacity}%`} detail="Population-weighted synthetic zone input" icon={BedDouble} tone={summary.shelterCapacity < 40 ? 'amber' : 'green'} />
        <StatCard label="RESOURCE SHORTAGE" value={shortageTypes.length ? shortageTypes[0] : 'NONE'} detail={shortageTypes.length ? `${shortageTypes.length} resource types below modeled need` : 'Modeled inventory covers active report needs'} icon={Droplet} tone={shortageTypes.length ? 'critical' : 'green'} />
      </section>
      <section className="overview-grid">
        <article className="panel risk-distribution-panel"><div className="panel-heading"><div><p className="eyebrow">MODEL OUTPUT</p><h3>Risk distribution</h3></div><span className="panel-meta">{zones.length} ZONES</span></div><RiskChart distribution={summary.distribution} /></article>
        <article className="panel signal-panel"><div className="panel-heading"><div><p className="eyebrow">PRIORITY SIGNALS</p><h3>Zone posture</h3></div><span className="panel-meta">DEMO INPUTS</span></div>
          <div className="posture-list">{riskLevels.slice().reverse().map((level) => <div className={`posture-row posture-${level.toLowerCase()}`} key={level}><span className="posture-mark" /><span className="posture-name">{level} RISK</span><strong>{summary.distribution[level]}</strong><span className="posture-unit">zones</span></div>)}</div>
          <div className="posture-footnote"><span>Population across zones</span><strong>{formatNumber.format(summary.totalPopulation)}</strong></div>
          {summary.highestRisk && <Link className="text-link" to={`/map?zone=${encodeURIComponent(summary.highestRisk.zone_id)}`}>Locate highest-risk zone <ArrowUpRight size={15} /></Link>}
        </article>
      </section>
      <section className="panel zones-panel"><div className="panel-heading panel-heading-table"><div><p className="eyebrow">SYNTHETIC ZONE REGISTER</p><h3>Flood risk by zone</h3></div><Link className="button button-quiet" to="/map">Open risk map <ArrowUpRight size={15} /></Link></div><ZoneTable zones={zones} /></section>
      <p className="model-footnote">Risk scores and affected-population values are reproducible MVP estimates, not official forecasts.</p>
    </div>
  )
}