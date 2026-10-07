import { useEffect, useMemo, useState } from 'react'
import { divIcon } from 'leaflet'
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { getReports, getZoneAssessments } from '../api/client'
import LoadingState, { ErrorState } from '../components/LoadingState'
import RiskBadge from '../components/RiskBadge'

const numberFormat = new Intl.NumberFormat('en')

function createZoneIcon(zone, selected) {
  const level = zone.risk.risk_level.toLowerCase()
  return divIcon({ className: 'zone-marker-container', html: `<span class="zone-map-marker zone-marker-${level} ${selected ? 'zone-marker-selected' : ''}"><b>${zone.risk.risk_score}</b></span>`, iconSize: [44, 44], iconAnchor: [22, 22] })
}

function reportMarkerPosition(report, reports) {
  const colocated = reports.filter((item) => Math.abs(item.latitude - report.latitude) < 0.0001 && Math.abs(item.longitude - report.longitude) < 0.0001)
  if (colocated.length < 2) return [report.latitude, report.longitude]
  const index = colocated.findIndex((item) => item.report_id === report.report_id)
  const angle = 2 * Math.PI * index / colocated.length
  const spread = 0.00018
  return [report.latitude + Math.cos(angle) * spread, report.longitude + Math.sin(angle) * spread]
}

const priorityColors = { LOW: '#31816b', MEDIUM: '#b68a25', HIGH: '#cf7134', CRITICAL: '#b9473d' }

function FitZoneBounds({ zones, reports, selectedZone, selectedReport }) {
  const map = useMap()
  useEffect(() => {
    const report = reports.find((item) => item.report_id === selectedReport)
    if (report) {
      map.setView([report.latitude, report.longitude], 14, { animate: false })
      return
    }
    const target = zones.find((zone) => zone.zone_id === selectedZone)
    if (target) map.setView([target.latitude, target.longitude], 13, { animate: false })
    else if (zones.length || reports.length) map.fitBounds([...zones.map((zone) => [zone.latitude, zone.longitude]), ...reports.map((item) => [item.latitude, item.longitude])], { padding: [42, 42] })
  }, [map, reports, selectedReport, selectedZone, zones])
  return null
}

function ReportMarkerPane() {
  const map = useMap()
  useEffect(() => {
    if (!map.getPane('reportMarkers')) {
      map.createPane('reportMarkers')
      map.getPane('reportMarkers').style.zIndex = '650'
    }
  }, [map])
  return null
}

export default function RiskMap() {
  const [zones, setZones] = useState([])
  const [reports, setReports] = useState([])
  const [reportsError, setReportsError] = useState(null)
  const [dataLabel, setDataLabel] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reload, setReload] = useState(0)
  const [searchParams] = useSearchParams()
  const selectedZone = searchParams.get('zone')
  const selectedReport = searchParams.get('report')
  const zoneIcons = useMemo(() => Object.fromEntries(zones.map((zone) => [zone.zone_id, createZoneIcon(zone, zone.zone_id === selectedZone)])), [selectedZone, zones])
  const refresh = () => {
    setLoading(true)
    setError(null)
    setReload((value) => value + 1)
  }

  useEffect(() => {
    let active = true
    Promise.allSettled([getZoneAssessments(), getReports()]).then(([zonesResult, reportsResult]) => {
      if (!active) return
      if (zonesResult.status === 'fulfilled') {
        setZones(zonesResult.value.zones)
        setDataLabel(zonesResult.value.dataLabel)
      } else setError(zonesResult.reason)
      if (reportsResult.status === 'fulfilled') setReports(reportsResult.value.reports)
      else setReportsError(reportsResult.reason)
    }).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [reload])

  if (loading) return <LoadingState label="Loading synthetic zone coordinates" />
  if (error) return <ErrorState error={error} onRetry={refresh} />
  const center = zones.length ? [zones[0].latitude, zones[0].longitude] : reports.length ? [reports[0].latitude, reports[0].longitude] : [19.076, 72.8777]

  return (
    <div className="page-stack page-enter">
      <section className="page-intro"><div><p className="eyebrow">GEOSPATIAL VIEW · URBAN FLOOD</p><h2>Risk map</h2><p className="intro-copy">Model-scored synthetic zones on OpenStreetMap. Markers show risk score out of 100.</p></div><span className="data-source-tag">{dataLabel}</span></section>
      <section className="map-key" aria-label="Map risk legend">{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => <span className={`map-key-item key-${level.toLowerCase()}`} key={level}><i /> {level}</span>)}<span className="map-key-note">OSM tiles · third-party map data</span></section>
      {reportsError && <div className="map-report-warning" role="status">Report locations could not be loaded: {reportsError.message}</div>}
      <section className="map-key report-map-key" aria-label="Report marker legend"><strong>REPORT SIGNALS</strong><span className="report-dot report-critical-dot" /> Critical priority <span className="report-dot report-high-dot" /> High priority <span className="report-dot report-other-dot" /> Other reports</section>
      <section className="map-panel" aria-label="Map of synthetic flood risk zones and citizen reports"><MapContainer center={center} zoom={11} scrollWheelZoom={false} className="risk-leaflet-map">
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <FitZoneBounds zones={zones} reports={reports} selectedZone={selectedZone} selectedReport={selectedReport} />
        <ReportMarkerPane />
        {zones.map((zone) => <Marker key={zone.zone_id} position={[zone.latitude, zone.longitude]} icon={zoneIcons[zone.zone_id]}><Popup><div className="map-popup"><div className="map-popup-top"><strong>{zone.name}</strong><RiskBadge level={zone.risk.risk_level} compact /></div><span>{zone.zone_id} · SYNTHETIC</span><dl><div><dt>Risk score</dt><dd>{zone.risk.risk_score} / 100</dd></div><div><dt>Population</dt><dd>{numberFormat.format(zone.population)}</dd></div><div><dt>Estimated affected</dt><dd>{numberFormat.format(zone.simulation.affected_population)}</dd></div></dl></div></Popup></Marker>)}
        {reports.map((report) => <CircleMarker key={report.report_id} pane="reportMarkers" center={reportMarkerPosition(report, reports)} radius={report.report_id === selectedReport ? 11 : 8} pathOptions={{ className: `report-marker report-marker-${report.report_id.toLowerCase()}`, color: '#ffffff', weight: 2, fillColor: priorityColors[report.priority_level] || '#66766f', fillOpacity: 0.96 }}>
          <Popup><div className="map-popup report-map-popup"><div className="map-popup-top"><strong>{report.report_id}</strong><RiskBadge level={report.priority_level} compact /></div><h4>{report.category.replace('_', ' ')}</h4><p>{report.title}</p><dl><div><dt>Severity</dt><dd>{report.severity} / 5</dd></div><div><dt>Priority</dt><dd>{report.priority_score} / 100</dd></div><div><dt>People affected</dt><dd>{numberFormat.format(report.people_affected)}</dd></div><div><dt>Status</dt><dd>{report.status}</dd></div><div><dt>Reported location</dt><dd>{report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}</dd></div></dl><Link className="map-report-link" to={`/reports?report=${encodeURIComponent(report.report_id)}`}>Open report details</Link></div></Popup>
        </CircleMarker>)}
      </MapContainer></section>
      <p className="model-footnote">Coordinates and risk results are fictional demonstration data. Map tiles depend on OpenStreetMap service availability and policy.</p>
    </div>
  )
}