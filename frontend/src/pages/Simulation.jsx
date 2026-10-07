import { useState } from 'react'
import { Activity, ArrowRight, Droplet, HeartPulse, House, Package, Play } from 'lucide-react'
import { simulateFlood } from '../api/client'
import LoadingState, { ErrorState } from '../components/LoadingState'
import RiskBadge from '../components/RiskBadge'

const initialValues = { total_population: '18000', rainfall_mm: '210', river_level: 'HIGH', population_density: '8000', road_accessibility: '40', shelter_capacity: '35', medical_capacity: '40', historical_risk: '70' }
const fields = [
  { key: 'rainfall_mm', label: 'Rainfall', unit: 'mm', min: 0, max: 500, step: 1 },
  { key: 'population_density', label: 'Population density', unit: 'people / km²', min: 0, max: 50000, step: 100 },
  { key: 'road_accessibility', label: 'Road accessibility', unit: '% accessible', min: 0, max: 100, step: 1 },
  { key: 'shelter_capacity', label: 'Shelter adequacy', unit: '% adequate', min: 0, max: 100, step: 1 },
  { key: 'medical_capacity', label: 'Medical capacity', unit: '% available', min: 0, max: 100, step: 1 },
  { key: 'historical_risk', label: 'Historical risk index', unit: '0–100', min: 0, max: 100, step: 1 },
]
const formatNumber = new Intl.NumberFormat('en')

function ResultMetric({ icon: Icon, label, value, unit }) {
  return <div className="result-metric"><span className="result-metric-icon"><Icon size={17} /></span><span className="result-metric-label">{label}</span><strong>{formatNumber.format(value)}</strong><span className="result-metric-unit">{unit}</span></div>
}

export default function Simulation() {
  const [values, setValues] = useState(initialValues)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  function updateValue(key, value) { setValues((current) => ({ ...current, [key]: value })) }

  async function submitSimulation(event) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    const payload = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, key === 'river_level' ? value : Number(value)]))
    try { setResult(await simulateFlood(payload)) }
    catch (requestError) { setError(requestError) }
    finally { setLoading(false) }
  }

  return (
    <div className="page-stack page-enter">
      <section className="page-intro"><div><p className="eyebrow">DECISION SUPPORT · LOCAL MODEL</p><h2>Flood simulation</h2><p className="intro-copy">Adjust zone conditions and review the model’s estimated impact and factors.</p></div><span className="data-source-tag">SYNTHETIC SCENARIO</span></section>
      <div className="simulation-layout">
        <section className="panel simulation-form-panel"><div className="panel-heading"><div><p className="eyebrow">SCENARIO INPUTS</p><h3>Zone conditions</h3></div><span className="panel-meta">CUSTOM</span></div>
          <form className="simulation-form" onSubmit={submitSimulation}>
            <label className="field-block population-field"><span className="field-heading"><span>Total population</span><small>people</small></span><input type="number" min="1" max="10000000" value={values.total_population} onChange={(event) => updateValue('total_population', event.target.value)} required /></label>
            <label className="field-block river-field"><span className="field-heading"><span>River level</span><small>observed band</small></span><select value={values.river_level} onChange={(event) => updateValue('river_level', event.target.value)}>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => <option value={level} key={level}>{level}</option>)}</select></label>
            {fields.map((field) => <label className="field-block" key={field.key}><span className="field-heading"><span>{field.label}</span><small>{field.unit}</small></span><div className="range-input-row">
              <input type="range" min={field.min} max={field.max} step={field.step} value={values[field.key]} onChange={(event) => updateValue(field.key, event.target.value)} aria-label={field.label} />
              <input className="range-number" type="number" min={field.min} max={field.max} step={field.step} value={values[field.key]} onChange={(event) => updateValue(field.key, event.target.value)} required />
            </div></label>)}
            <button className="button button-primary simulation-submit" type="submit" disabled={loading}><Play size={16} fill="currentColor" />{loading ? 'RUNNING MODEL…' : 'RUN FLOOD SIMULATION'}{!loading && <ArrowRight size={16} />}</button>
            <p className="form-note">Results are deterministic demo estimates. Review local conditions and official guidance before action.</p>
          </form>
        </section>
        <section className="simulation-output" aria-live="polite">
          {!result && !loading && !error && <div className="panel simulation-empty"><div className="empty-illustration"><Activity size={24} /></div><p className="eyebrow">MODEL READY</p><h3>Run a flood scenario</h3><p>Set the zone conditions, then submit to receive a risk score, estimated needs, and explainable factors from the backend.</p></div>}
          {loading && <div className="panel"><LoadingState label="Calculating risk and estimated demand" /></div>}
          {error && <ErrorState error={error} onRetry={submitSimulation} />}
          {result && <div className="result-stack">
            <article className={`result-hero result-${result.risk.risk_level.toLowerCase()}`}><div className="result-hero-top"><div><p className="eyebrow">MODEL RESULT · {result.scenario} SCENARIO</p><h3>Risk assessment</h3></div><RiskBadge level={result.risk.risk_level} /></div>
              <div className="result-score-row"><strong>{result.risk.risk_score}</strong><span>/ 100</span><div className="score-track"><i style={{ width: `${result.risk.risk_score}%` }} /></div></div><p>{result.risk.model_notice}</p>
            </article>
            <article className="panel result-demand-panel"><div className="panel-heading"><div><p className="eyebrow">ONE-DAY PLANNING ESTIMATE</p><h3>Estimated impact & demand</h3></div></div>
              <div className="affected-population"><span className="affected-icon"><Activity size={18} /></span><span>Affected population</span><strong>{formatNumber.format(result.affected_population)}</strong><small>of {formatNumber.format(Number(values.total_population))} people</small></div>
              <div className="result-metric-grid"><ResultMetric icon={Droplet} label="Water" value={result.demand.water_litres} unit="litres / day" /><ResultMetric icon={Package} label="Food" value={result.demand.food_kits} unit="kits / day" /><ResultMetric icon={HeartPulse} label="Medical" value={result.demand.medical_units} unit="units / day" /><ResultMetric icon={House} label="Shelter" value={result.demand.shelter_spaces} unit="spaces" /></div>
              <p className="assumptions-note">{result.demand.notice} Defaults: {result.demand.assumptions.water_litres_per_person} L/person, {result.demand.assumptions.food_kits_per_person} food kit/person, {result.demand.assumptions.medical_units_per_person} medical units/person, and {result.demand.assumptions.shelter_spaces_per_person} shelter spaces/person.</p>
            </article>
            <article className="panel why-panel"><div className="panel-heading"><div><p className="eyebrow">TRANSPARENT MODEL</p><h3>Why is this risk level?</h3></div><span className="panel-meta">{result.risk.model_version}</span></div>
              <div className="factor-list">{result.risk.factor_details.map((factor) => <div className="factor-row" key={factor.factor}><div className="factor-heading"><span>{factor.factor.replaceAll('_', ' ')}</span><RiskBadge level={factor.rating} compact /></div><div className="factor-track"><i style={{ width: `${factor.normalized_risk}%` }} /></div><p>{factor.reason}<span> +{factor.contribution.toFixed(2)} pts</span></p></div>)}</div>
            </article>
            <article className="panel actions-panel"><div className="panel-heading"><div><p className="eyebrow">HUMAN REVIEW REQUIRED</p><h3>Recommended actions</h3></div></div><ol className="action-list">{result.recommended_actions.map((action, index) => <li key={action}><span>{String(index + 1).padStart(2, '0')}</span>{action}</li>)}</ol></article>
          </div>}
        </section>
      </div>
    </div>
  )
}