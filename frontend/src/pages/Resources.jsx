import { useEffect, useState } from 'react'
import { ArrowDownToLine, BedDouble, Droplet, HeartPulse, Package, RefreshCw, Utensils } from 'lucide-react'
import { allocateResource, getAllocations, getReports, getResourceShortages, getResourceSummary, getResources, matchResources } from '../api/client'
import LoadingState, { ErrorState } from '../components/LoadingState'

const resourceIcons = { WATER: Droplet, FOOD: Utensils, MEDICINE: HeartPulse, SHELTER: BedDouble, AMBULANCE: Package }
const displayNames = { WATER: 'Water', FOOD: 'Food', MEDICINE: 'Medicine', SHELTER: 'Shelter', AMBULANCE: 'Ambulances' }
const formatQuantity = (value) => Number(value).toLocaleString('en', { maximumFractionDigits: 2 })

async function loadResourceWorkspace() {
  const [summary, resourceResponse, shortageResponse, allocationResponse, reportResponse] = await Promise.all([
    getResourceSummary(), getResources(), getResourceShortages(), getAllocations(), getReports(),
  ])
  return {
    summary,
    resources: resourceResponse.resources,
    dataLabel: resourceResponse.data_label,
    shortages: shortageResponse.shortages,
    allocations: allocationResponse.allocations,
    reports: reportResponse.reports.filter((report) => !['RESOLVED', 'REJECTED'].includes(report.status)),
  }
}

export default function Resources() {
  const [workspace, setWorkspace] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reload, setReload] = useState(0)
  const [selectedReportId, setSelectedReportId] = useState('')
  const [selectedType, setSelectedType] = useState('WATER')
  const [matching, setMatching] = useState(false)
  const [matchResult, setMatchResult] = useState(null)
  const [matchError, setMatchError] = useState(null)
  const [pendingAllocation, setPendingAllocation] = useState(null)
  const [allocating, setAllocating] = useState(false)
  const [notice, setNotice] = useState(null)

  useEffect(() => {
    let active = true
    loadResourceWorkspace().then((result) => {
      if (!active) return
      setWorkspace(result)
      setSelectedReportId((current) => result.reports.some((report) => report.report_id === current) ? current : result.reports[0]?.report_id || '')
    }).catch((requestError) => active && setError(requestError)).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [reload])

  function refresh() {
    setLoading(true)
    setError(null)
    setReload((value) => value + 1)
  }

  const selectedReport = workspace?.reports.find((report) => report.report_id === selectedReportId)

  async function runMatch(event) {
    event?.preventDefault()
    if (!selectedReport) return
    setMatching(true)
    setMatchError(null)
    setMatchResult(null)
    try {
      const result = await matchResources({
        report_id: selectedReport.report_id,
        latitude: selectedReport.latitude,
        longitude: selectedReport.longitude,
        affected_population: Math.max(1, selectedReport.people_affected),
        risk_level: selectedReport.priority_level,
        resource_type: selectedType,
      })
      setMatchResult(result)
    } catch (requestError) {
      setMatchError(requestError)
    } finally {
      setMatching(false)
    }
  }

  async function confirmAllocation() {
    if (!pendingAllocation || !selectedReport) return
    setAllocating(true)
    setError(null)
    try {
      const allocation = await allocateResource({
        resource_id: pendingAllocation.resource_id,
        quantity: pendingAllocation.recommended_quantity,
        report_id: selectedReport.report_id,
        actor: 'LOCAL_OPERATOR',
        reason: `MVP match recommendation for ${selectedReport.report_id}`,
      })
      setPendingAllocation(null)
      setNotice(`Allocated ${formatQuantity(allocation.quantity)} ${allocation.unit} from ${allocation.resource_name}. Remaining inventory: ${formatQuantity(allocation.remaining_inventory)} ${allocation.unit}.`)
      const updatedWorkspace = await loadResourceWorkspace()
      setWorkspace(updatedWorkspace)
      const updatedMatch = await matchResources({
        report_id: selectedReport.report_id,
        latitude: selectedReport.latitude,
        longitude: selectedReport.longitude,
        affected_population: Math.max(1, selectedReport.people_affected),
        risk_level: selectedReport.priority_level,
        resource_type: selectedType,
      })
      setMatchResult(updatedMatch)
    } catch (requestError) {
      setError(requestError)
    } finally {
      setAllocating(false)
    }
  }

  if (loading && !workspace) return <LoadingState label="Loading synthetic inventory and report requirements" />
  if (error && !workspace) return <ErrorState error={error} onRetry={refresh} />

  return <div className="page-stack page-enter">
    <section className="page-intro"><div><p className="eyebrow">RESPONSE INVENTORY · {workspace?.summary.open_report_count || 0} ACTIVE REPORTS</p><h2>Resource status</h2><p className="intro-copy">Compare modeled requirements against local stock and coordinate a reviewable allocation.</p></div><div className="resource-page-actions"><span className="data-source-tag">{workspace?.dataLabel}</span><button className="icon-button" type="button" title="Refresh resource data" aria-label="Refresh resource data" onClick={refresh} disabled={loading}><RefreshCw size={16} /></button></div></section>

    {error && <ErrorState error={error} onRetry={refresh} />}
    {notice && <div className="operation-notice operation-success" role="status"><span className="notice-success-mark" /><p>{notice}</p><button type="button" onClick={() => setNotice(null)}>Dismiss</button></div>}

    <section className="resource-coverage-grid" aria-label="Resource requirements and coverage">
      {workspace?.summary.resources.map((item) => {
        const Icon = resourceIcons[item.type]
        return <article className={`panel coverage-card ${item.shortage > 0 ? 'coverage-short' : ''}`} key={item.type}>
          <div className="coverage-card-heading"><span className="resource-icon resource-neutral"><Icon size={18} /></span><span>{displayNames[item.type]}</span><small>{item.unit}</small></div>
          <div className="coverage-amounts"><div><small>REQUIRED</small><strong>{formatQuantity(item.required)}</strong></div><div><small>AVAILABLE</small><strong>{formatQuantity(item.available)}</strong></div></div>
          <div className="coverage-track"><i style={{ width: `${item.coverage_percent}%` }} /></div>
          <div className="coverage-foot"><span>{formatQuantity(item.coverage_percent)}% coverage</span>{item.shortage > 0 ? <strong>{formatQuantity(item.shortage)} short</strong> : <span className="coverage-met">Requirement covered</span>}</div>
        </article>
      })}
    </section>

    <section className="resource-work-grid">
      <article className="panel shortage-panel"><div className="panel-heading"><div><p className="eyebrow">ACTIVE NEEDS</p><h3>Resource shortages</h3></div><span className="panel-meta">{workspace?.shortages.length || 0} TYPES</span></div>
        {workspace?.shortages.length ? <div className="shortage-list">{workspace.shortages.map((item) => <div className="shortage-row" key={item.type}><span className="shortage-alert" /> <span>{displayNames[item.type]}</span><strong>{formatQuantity(item.shortage)} {item.unit}</strong><small>{formatQuantity(item.coverage_percent)}% covered</small></div>)}</div> : <div className="resource-empty-state"><span className="coverage-met">No modeled shortage</span><p>Current synthetic inventory covers the aggregate demand from active local reports.</p></div>}
        <p className="resource-assumption-note">Required quantities sum per-report estimates using the assumptions returned by the backend. Values are synthetic planning estimates, not official guidance.</p>
      </article>

      <article className="panel matching-panel"><div className="panel-heading"><div><p className="eyebrow">LIFEGRID MVP RESOURCE MATCHING HEURISTIC</p><h3>Match resources to an incident</h3></div></div>
        <form className="match-form" onSubmit={runMatch}>
          <label className="field-block"><span className="field-heading"><span>Incident</span><small>active report</small></span><select value={selectedReportId} onChange={(event) => { setSelectedReportId(event.target.value); setMatchResult(null); setMatchError(null) }} disabled={!workspace?.reports.length}><option value="">{workspace?.reports.length ? 'Select a report' : 'No active reports'}</option>{workspace?.reports.map((report) => <option key={report.report_id} value={report.report_id}>{report.report_id} · {report.title}</option>)}</select></label>
          <label className="field-block"><span className="field-heading"><span>Resource type</span></span><select value={selectedType} onChange={(event) => { setSelectedType(event.target.value); setMatchResult(null) }}>{Object.entries(displayNames).map(([type, label]) => <option value={type} key={type}>{label}</option>)}</select></label>
          <button className="button button-primary" type="submit" disabled={!selectedReport || matching}><Package size={15} />{matching ? 'MATCHING…' : 'MATCH RESOURCES'}</button>
        </form>
        {matchError && <ErrorState error={matchError} />}
        {matching && <LoadingState label="Ranking nearby resources by distance and available stock" />}
        {matchResult && <div className="match-result" aria-live="polite">
          <div className="match-result-summary"><div><span>REQUIRED</span><strong>{formatQuantity(matchResult.required_quantity)} {matchResult.recommendations[0]?.unit || workspace.resources.find((resource) => resource.type === selectedType)?.unit}</strong></div><div><span>RECOMMENDED</span><strong>{formatQuantity(matchResult.recommended_quantity)}</strong></div><div className={matchResult.shortage_quantity > 0 ? 'shortage-value' : 'coverage-met'}><span>SHORTAGE</span><strong>{formatQuantity(matchResult.shortage_quantity)}</strong></div></div>
          {matchResult.recommendations.length ? <div className="table-scroll"><table className="zone-table match-table"><thead><tr><th scope="col">Resource</th><th scope="col">Distance</th><th scope="col">Available</th><th scope="col">Recommend</th><th scope="col">Action</th></tr></thead><tbody>{matchResult.recommendations.map((recommendation) => <tr key={recommendation.resource_id}><th scope="row"><span className="zone-name">{recommendation.name}</span><span className="zone-id">{recommendation.resource_id}</span></th><td>{recommendation.distance_km} km</td><td>{formatQuantity(recommendation.available_quantity)} {recommendation.unit}</td><td><strong>{formatQuantity(recommendation.recommended_quantity)}</strong></td><td><button className="button button-small button-secondary" type="button" onClick={() => setPendingAllocation(recommendation)} disabled={allocating}><ArrowDownToLine size={13} /> Allocate</button></td></tr>)}</tbody></table></div> : <div className="resource-empty-state"><p>No available matching resources were found within the risk-based search radius.</p></div>}
          <p className="resource-assumption-note">{matchResult.notice} {matchResult.method}. {matchResult.recommendations[0]?.reason}</p>
        </div>}
      </article>
    </section>

    <section className="resource-work-grid inventory-grid">
      <article className="panel inventory-table-panel"><div className="panel-heading"><div><p className="eyebrow">BASE FIXTURE MINUS APPENDED ALLOCATIONS</p><h3>Current inventory</h3></div><span className="panel-meta">{workspace?.resources.length || 0} RECORDS</span></div>
        <div className="table-scroll"><table className="zone-table"><thead><tr><th scope="col">Resource hub</th><th scope="col">Type</th><th scope="col">Available</th><th scope="col">Capacity</th><th scope="col">Status</th></tr></thead><tbody>{workspace?.resources.map((resource) => <tr key={resource.resource_id}><th scope="row"><span className="zone-name">{resource.name}</span><span className="zone-id">{resource.resource_id}</span></th><td>{resource.type}</td><td>{formatQuantity(resource.available_quantity)} {resource.unit}</td><td>{formatQuantity(resource.capacity)} {resource.unit}</td><td><span className={`status-pill status-${resource.status.toLowerCase()}`}>{resource.status}</span></td></tr>)}</tbody></table></div>
      </article>
      <article className="panel allocation-history-panel"><div className="panel-heading"><div><p className="eyebrow">APPEND-ONLY LOCAL HISTORY</p><h3>Recent allocations</h3></div><span className="panel-meta">{workspace?.allocations.length || 0}</span></div>
        {workspace?.allocations.length ? <div className="allocation-list">{workspace.allocations.slice(0, 8).map((allocation) => <div className="allocation-history-row" key={allocation.allocation_id}><span className="allocation-history-mark"><ArrowDownToLine size={14} /></span><div><strong>{formatQuantity(allocation.quantity)} {allocation.unit} · {allocation.resource_name}</strong><small>{allocation.allocation_id} · {allocation.report_id || 'Unlinked'} · {new Date(allocation.timestamp).toLocaleString()}</small></div></div>)}</div> : <div className="resource-empty-state"><p>No allocations recorded. Confirming a match recommendation will create the first history entry.</p></div>}
      </article>
    </section>

    {pendingAllocation && <div className="modal-backdrop" role="presentation"><section className="confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="allocation-confirm-title"><p className="eyebrow">INVENTORY CHANGE · HUMAN CONFIRMATION</p><h3 id="allocation-confirm-title">Allocate recommended stock?</h3><p><strong>{formatQuantity(pendingAllocation.recommended_quantity)} {pendingAllocation.unit}</strong> from {pendingAllocation.name} to {selectedReport?.report_id}. This will update derived available inventory and append an allocation record.</p><div className="modal-actions"><button className="button button-secondary" type="button" onClick={() => setPendingAllocation(null)} disabled={allocating}>Cancel</button><button className="button button-primary" type="button" onClick={confirmAllocation} disabled={allocating}>{allocating ? 'ALLOCATING…' : 'CONFIRM ALLOCATION'}</button></div></section></div>}
  </div>
}