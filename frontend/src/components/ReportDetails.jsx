import { useState } from 'react'
import { ArrowUpRight, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import RiskBadge from './RiskBadge'

const transitions = {
  RECEIVED: ['VALIDATING', 'REJECTED'],
  VALIDATING: ['VERIFIED', 'REJECTED'],
  VERIFIED: ['DISPATCHED', 'REJECTED'],
  DISPATCHED: ['RESOLVED'],
  RESOLVED: [],
  REJECTED: [],
}

export default function ReportDetails({ report, onStatusUpdate, onDelete, onClose, busy }) {
  const [chosenStatus, setChosenStatus] = useState(null)
  const nextStatus = chosenStatus || transitions[report?.status]?.[0] || ''
  if (!report) return null
  return <aside className="report-detail-panel" aria-label={`Report details ${report.report_id}`}>
    <div className="detail-heading"><div><p className="eyebrow">REPORT DETAILS</p><strong>{report.report_id}</strong></div><button className="icon-button" type="button" title="Close report details" aria-label="Close report details" onClick={onClose}><X size={17} /></button></div>
    {report.possible_duplicate && <div className="duplicate-warning" role="note"><strong>Possible duplicate</strong><span>Cross-check before action. This report was retained.</span><div>{report.duplicate_report_ids.map((id) => <span className="duplicate-id" key={id}>{id}</span>)}</div></div>}
    <div className="report-detail-title"><span>{report.category.replace('_', ' ')}</span><h3>{report.title}</h3><p>{report.description}</p></div>
    <div className="detail-priority"><span>Priority</span><RiskBadge level={report.priority_level} /><strong>{report.priority_score}<small> / 100</small></strong></div>
    <dl className="report-detail-grid"><div><dt>Severity</dt><dd>{report.severity} / 5</dd></div><div><dt>People affected</dt><dd>{report.people_affected.toLocaleString()}</dd></div><div><dt>Status</dt><dd><span className={`status-pill status-${report.status.toLowerCase()}`}>{report.status}</span></dd></div><div><dt>Source</dt><dd>{report.source}</dd></div><div><dt>Coordinates</dt><dd>{report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}</dd></div><div><dt>Location risk</dt><dd>{report.location_risk_score} / 100</dd></div></dl>
    <div className="priority-explanation"><strong>Priority explanation</strong><ul>{report.priority_explanation.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
    <div className="status-history"><strong>Status history</strong>{report.status_history.map((event, index) => <div className="status-history-row" key={`${event.timestamp}-${index}`}><span>{event.status}</span><small>{event.actor} · {event.reason}</small></div>)}</div>
    <div className="detail-actions">
      {transitions[report.status]?.length > 0 && <label className="field-block"><span className="field-heading"><span>Next status</span></span><select value={nextStatus} onChange={(event) => setChosenStatus(event.target.value)} disabled={busy} aria-label="Next report status">{transitions[report.status].map((status) => <option key={status}>{status}</option>)}</select></label>}
      {transitions[report.status]?.length > 0 && <button className="button button-secondary" type="button" disabled={busy} onClick={() => onStatusUpdate(nextStatus)}>Update status</button>}
      <Link className="button button-quiet" to={`/map?report=${encodeURIComponent(report.report_id)}`}><ArrowUpRight size={14} /> Map</Link>
      <button className="button button-danger-quiet" type="button" disabled={busy} onClick={onDelete}><Trash2 size={14} /> Delete</button>
    </div>
  </aside>
}