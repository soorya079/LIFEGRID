import { useState } from 'react'
import { AlertTriangle, Send, X } from 'lucide-react'

const categories = ['FLOOD', 'ROAD_BLOCK', 'MEDICAL', 'SHELTER', 'FOOD', 'WATER', 'FIRE', 'OTHER']

const blankReport = {
  category: 'FLOOD',
  title: '',
  description: '',
  latitude: '19.096',
  longitude: '72.8977',
  severity: '3',
  people_affected: '1',
}

export default function ReportForm({ onSubmit, onClose, submitting, error }) {
  const [values, setValues] = useState(blankReport)
  function change(key, value) {
    setValues((current) => ({ ...current, [key]: value }))
  }
  function submit(event) {
    event.preventDefault()
    onSubmit({
      ...values,
      latitude: Number(values.latitude),
      longitude: Number(values.longitude),
      severity: Number(values.severity),
      people_affected: Number(values.people_affected),
      source: 'CITIZEN',
    })
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && !submitting && onClose()}>
      <section className="report-form-modal" role="dialog" aria-modal="true" aria-labelledby="report-form-title">
        <div className="modal-heading">
          <div><p className="eyebrow">COMMUNITY INTAKE · LOCAL API</p><h3 id="report-form-title">Create emergency report</h3></div>
          <button className="icon-button" type="button" title="Close report form" aria-label="Close report form" onClick={onClose} disabled={submitting}><X size={18} /></button>
        </div>
        <div className="report-safety-note"><AlertTriangle size={15} /><span>Reports are unverified signals. For immediate danger, contact local emergency services.</span></div>
        <form className="report-form" onSubmit={submit}>
          <label className="field-block"><span className="field-heading"><span>Category</span></span><select value={values.category} onChange={(event) => change('category', event.target.value)}>{categories.map((category) => <option key={category} value={category}>{category.replace('_', ' ')}</option>)}</select></label>
          <label className="field-block"><span className="field-heading"><span>Severity</span><small>1 minor · 5 extreme</small></span><select value={values.severity} onChange={(event) => change('severity', event.target.value)}>{[1, 2, 3, 4, 5].map((severity) => <option key={severity} value={severity}>{severity} · {['Minor', 'Low', 'Moderate', 'High', 'Extreme'][severity - 1]}</option>)}</select></label>
          <label className="field-block report-form-wide"><span className="field-heading"><span>Short title</span><small>4–120 characters</small></span><input type="text" minLength={4} maxLength={120} value={values.title} onChange={(event) => change('title', event.target.value)} required placeholder="What is happening?" /></label>
          <label className="field-block report-form-wide"><span className="field-heading"><span>Description</span><small>8–2,000 characters</small></span><textarea rows="3" minLength={8} maxLength={2000} value={values.description} onChange={(event) => change('description', event.target.value)} required placeholder="Describe the observed conditions and immediate need." /></label>
          <label className="field-block"><span className="field-heading"><span>Latitude</span></span><input type="number" min="-90" max="90" step="any" value={values.latitude} onChange={(event) => change('latitude', event.target.value)} required /></label>
          <label className="field-block"><span className="field-heading"><span>Longitude</span></span><input type="number" min="-180" max="180" step="any" value={values.longitude} onChange={(event) => change('longitude', event.target.value)} required /></label>
          <label className="field-block"><span className="field-heading"><span>People affected</span><small>estimate</small></span><input type="number" min="0" max="1000000" value={values.people_affected} onChange={(event) => change('people_affected', event.target.value)} required /></label>
          {error && <div className="form-error report-form-wide" role="alert"><strong>{error.status ? `API ${error.status}` : 'Request failed'}</strong><span>{error.message}</span>{error.details?.length > 0 && <ul>{error.details.map((detail, index) => <li key={`${detail.location}-${index}`}>{detail.location}: {detail.message}</li>)}</ul>}</div>}
          <div className="modal-actions report-form-wide"><button className="button button-secondary" type="button" onClick={onClose} disabled={submitting}>Cancel</button><button className="button button-primary" type="submit" disabled={submitting}><Send size={15} />{submitting ? 'SUBMITTING…' : 'SUBMIT REPORT'}</button></div>
        </form>
      </section>
    </div>
  )
}