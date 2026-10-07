import { ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import RiskBadge from './RiskBadge'

const dateFormat = new Intl.DateTimeFormat('en', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })

export default function ReportTable({ reports, selectedId, onSelect }) {
  if (!reports.length) {
    return <div className="empty-table-state report-empty"><strong>No reports in the local queue</strong><span>Create a report to add a community signal to the map and matching workflow.</span></div>
  }
  return <div className="table-scroll"><table className="zone-table report-table">
    <thead><tr><th scope="col">Report</th><th scope="col">Category</th><th scope="col">Severity</th><th scope="col">Priority</th><th scope="col">Status</th><th scope="col">People</th><th scope="col">Received</th><th scope="col"><span className="sr-only">Map</span></th></tr></thead>
    <tbody>{reports.map((report) => <tr key={report.report_id} className={selectedId === report.report_id ? 'table-row-selected' : ''}>
      <td><button className="report-row-button" type="button" onClick={() => onSelect(report)}><strong>{report.report_id}</strong><span>{report.title}</span>{report.possible_duplicate && <em>POSSIBLE DUPLICATE</em>}</button></td>
      <td>{report.category.replace('_', ' ')}</td><td>{report.severity}/5</td><td><RiskBadge level={report.priority_level} compact /></td>
      <td><span className={`status-pill status-${report.status.toLowerCase()}`}>{report.status.replace('_', ' ')}</span></td>
      <td>{report.people_affected.toLocaleString()}</td><td>{dateFormat.format(new Date(report.timestamp))}</td>
      <td><Link className="table-action" to={`/map?report=${encodeURIComponent(report.report_id)}`} title={`Locate ${report.report_id} on the map`} aria-label={`Locate ${report.report_id} on the map`}><ExternalLink size={14} /></Link></td>
    </tr>)}</tbody>
  </table></div>
}