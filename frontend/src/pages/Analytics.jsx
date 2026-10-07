import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getZoneAssessments } from '../api/client'
import LoadingState, { ErrorState } from '../components/LoadingState'
import RiskChart from '../components/RiskChart'

const levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const colors = { LOW: '#31816b', MEDIUM: '#c39731', HIGH: '#d67835', CRITICAL: '#bd4d40' }
const incidentTrend = [{ label: 'D−5', reports: 8 }, { label: 'D−4', reports: 12 }, { label: 'D−3', reports: 9 }, { label: 'D−2', reports: 17 }, { label: 'D−1', reports: 22 }, { label: 'DEMO', reports: 31 }]

export default function Analytics() {
  const [zones, setZones] = useState([])
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
    getZoneAssessments().then((result) => active && setZones(result.zones)).catch((requestError) => active && setError(requestError)).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [reload])
  if (loading) return <LoadingState label="Preparing demo analytics" />
  if (error) return <ErrorState error={error} onRetry={refresh} />

  const distribution = Object.fromEntries(levels.map((level) => [level, zones.filter((zone) => zone.risk.risk_level === level).length]))
  const populationByRisk = levels.map((level) => ({ level, population: zones.filter((zone) => zone.risk.risk_level === level).reduce((sum, zone) => sum + zone.population, 0) }))
  const waterDemandByZone = zones.map((zone) => ({ name: zone.name, litres: zone.simulation.demand.water_litres }))
  const totalWater = waterDemandByZone.reduce((sum, zone) => sum + zone.litres, 0)

  return <div className="page-stack page-enter">
    <section className="page-intro"><div><p className="eyebrow">MEASUREMENT & REVIEW</p><h2>Analytics</h2><p className="intro-copy">Model-derived zone measures alongside clearly separated demo series.</p></div><span className="data-source-tag">ZONE METRICS · DEMO TREND</span></section>
    <section className="analytics-grid">
      <article className="panel analytics-risk-panel"><div className="panel-heading"><div><p className="eyebrow">BACKEND ASSESSMENTS</p><h3>Risk distribution</h3></div><span className="panel-meta">{zones.length} ZONES</span></div><RiskChart distribution={distribution} /></article>
      <article className="panel"><div className="panel-heading"><div><p className="eyebrow">SYNTHETIC POPULATION</p><h3>Population by risk</h3></div><span className="panel-meta">PEOPLE</span></div><div className="chart-wrap chart-medium"><ResponsiveContainer width="100%" height="100%"><BarChart data={populationByRisk} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e8eeeb" /><XAxis dataKey="level" tickLine={false} axisLine={false} tick={{ fill: '#60716e', fontSize: 10 }} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#80908d', fontSize: 10 }} /><Tooltip formatter={(value) => [Number(value).toLocaleString(), 'Population']} contentStyle={{ border: '1px solid #dce5e1', borderRadius: 6, fontSize: 12 }} /><Bar dataKey="population" radius={[3, 3, 0, 0]} maxBarSize={48}>{populationByRisk.map((entry) => <Cell key={entry.level} fill={colors[entry.level]} />)}</Bar></BarChart></ResponsiveContainer></div></article>
      <article className="panel"><div className="panel-heading"><div><p className="eyebrow">SIMULATION ENGINE</p><h3>Water demand by zone</h3></div><span className="panel-meta">LITRES / DAY</span></div><div className="chart-wrap chart-medium"><ResponsiveContainer width="100%" height="100%"><BarChart data={waterDemandByZone} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e8eeeb" /><XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#60716e', fontSize: 10 }} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#80908d', fontSize: 10 }} /><Tooltip formatter={(value) => [`${Number(value).toLocaleString()} L`, 'Water estimate']} contentStyle={{ border: '1px solid #dce5e1', borderRadius: 6, fontSize: 12 }} /><Bar dataKey="litres" fill="#367e8b" radius={[3, 3, 0, 0]} maxBarSize={48} /></BarChart></ResponsiveContainer></div><div className="chart-total"><span>Combined one-day estimate</span><strong>{totalWater.toLocaleString()} L</strong></div></article>
      <article className="panel"><div className="panel-heading"><div><p className="eyebrow">ILLUSTRATIVE SERIES · NOT API DATA</p><h3>Incident trend</h3></div><span className="panel-meta">DEMO</span></div><div className="chart-wrap chart-medium"><ResponsiveContainer width="100%" height="100%"><BarChart data={incidentTrend} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e8eeeb" /><XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#60716e', fontSize: 10 }} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#80908d', fontSize: 10 }} /><Tooltip formatter={(value) => [value, 'Illustrative reports']} contentStyle={{ border: '1px solid #dce5e1', borderRadius: 6, fontSize: 12 }} /><Bar dataKey="reports" fill="#c39731" radius={[3, 3, 0, 0]} maxBarSize={42} /></BarChart></ResponsiveContainer></div><p className="chart-disclaimer">Illustrative trend only; citizen report records are not connected.</p></article>
    </section>
  </div>
}