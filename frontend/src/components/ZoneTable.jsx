import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import RiskBadge from './RiskBadge'

const numberFormat = new Intl.NumberFormat('en')

export default function ZoneTable({ zones }) {
  return (
    <div className="table-scroll"><table className="zone-table">
      <thead><tr><th scope="col">Zone</th><th scope="col">Population</th><th scope="col">Risk</th><th scope="col">Score</th><th scope="col">Shelter</th><th scope="col">Medical</th><th scope="col">Road access</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
      <tbody>{zones.map((zone) => <tr key={zone.zone_id}>
        <th scope="row"><span className="zone-name">{zone.name}</span><span className="zone-id">{zone.zone_id}</span></th>
        <td>{numberFormat.format(zone.population)}</td><td><RiskBadge level={zone.risk.risk_level} compact /></td>
        <td><span className="score-value">{zone.risk.risk_score}</span><span className="score-out-of"> / 100</span></td>
        <td>{Math.round(zone.shelter_capacity)}%</td><td>{Math.round(zone.medical_capacity)}%</td><td>{Math.round(zone.road_accessibility)}%</td>
        <td><Link className="table-action" to={`/map?zone=${encodeURIComponent(zone.zone_id)}`} title={`Locate ${zone.name} on the risk map`} aria-label={`Locate ${zone.name} on the risk map`}><ArrowUpRight size={16} /></Link></td>
      </tr>)}</tbody>
    </table></div>
  )
}