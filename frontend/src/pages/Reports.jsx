import { useEffect, useState } from 'react'
import { AlertTriangle, FilePlus2, RefreshCw } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { createReport, deleteReport, getReports, updateReportStatus } from '../api/client'
import LoadingState, { ErrorState } from '../components/LoadingState'
import ReportDetails from '../components/ReportDetails'
import ReportForm from '../components/ReportForm'
import ReportTable from '../components/ReportTable'

export default function Reports() {
  const [reports, setReports] = useState([])
  const [dataLabel, setDataLabel] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [reload, setReload] = useState(0)
  const [formOpen, setFormOpen] = useState(false)
  const [selectedReportId, setSelectedReportId] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [notice, setNotice] = useState(null)
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    let active = true
    getReports().then((result) => {
      if (active) { setReports(result.reports); setDataLabel(result.data_label) }
    }).catch((requestError) => active && setError(requestError)).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [reload])

  function refresh() {
    setLoading(true)
    setError(null)
    setReload((value) => value + 1)
  }

  const queryReport = reports.find((report) => report.report_id === searchParams.get('report'))
  const selectedReport = queryReport || reports.find((report) => report.report_id === selectedReportId) || null

  async function submitReport(values) {
    setBusy(true)
    setFormError(null)
    setNotice(null)
    try {
      const report = await createReport(values)
      setSelectedReportId(report.report_id)
      setFormOpen(false)
      setNotice({
        kind: report.possible_duplicate ? 'warning' : 'success',
        text: report.possible_duplicate
          ? `Report ${report.report_id} was saved and may duplicate ${report.duplicate_report_ids.join(', ')}. It was retained for review.`
          : `Report ${report.report_id} was received and added to the local queue.`,
      })
      refresh()
    } catch (requestError) {
      setFormError(requestError)
    } finally {
      setBusy(false)
    }
  }

  async function changeStatus(status) {
    if (!selectedReport) return
    setBusy(true)
    setError(null)
    try {
      const updated = await updateReportStatus(selectedReport.report_id, {
        status,
        actor: 'LOCAL_OPERATOR',
        reason: `Status updated to ${status} in local operations UI`,
      })
      setSelectedReportId(updated.report_id)
      setNotice({ kind: 'success', text: `${updated.report_id} status updated to ${updated.status}.` })
      refresh()
    } catch (requestError) {
      setError(requestError)
    } finally {
      setBusy(false)
    }
  }

  async function confirmDelete() {
    if (!selectedReport) return
    setBusy(true)
    try {
      await deleteReport(selectedReport.report_id)
      setNotice({ kind: 'success', text: `${selectedReport.report_id} was deleted from the local report store.` })
      setSelectedReportId(null)
      setDeleteConfirm(false)
      refresh()
    } catch (requestError) {
      setError(requestError)
      setDeleteConfirm(false)
    } finally {
      setBusy(false)
    }
  }

  const activeCount = reports.filter((report) => !['RESOLVED', 'REJECTED'].includes(report.status)).length
  const criticalCount = reports.filter((report) => report.priority_level === 'CRITICAL').length
  const duplicateCount = reports.filter((report) => report.possible_duplicate).length

  return <div className="page-stack page-enter">
    <section className="page-intro"><div><p className="eyebrow">COMMUNITY SIGNALS · {reports.length} STORED</p><h2>Citizen reports</h2><p className="intro-copy">Record a community signal, review its heuristic priority, and track operator status.</p></div>
      <div className="report-page-actions"><span className="data-source-tag">{dataLabel}</span><button className="button button-primary" type="button" onClick={() => { setFormError(null); setFormOpen(true) }}><FilePlus2 size={16} /> CREATE EMERGENCY REPORT</button></div>
    </section>
    {notice && <div className={`operation-notice operation-${notice.kind}`} role="status"><span>{notice.kind === 'warning' ? <AlertTriangle size={17} /> : <span className="notice-success-mark" />}</span><p>{notice.text}</p><button type="button" aria-label="Dismiss notice" onClick={() => setNotice(null)}>Dismiss</button></div>}
    {error && <ErrorState error={error} onRetry={refresh} />}
    <section className="report-stat-grid" aria-label="Report queue statistics">
      <article><span>ACTIVE QUEUE</span><strong>{activeCount}</strong><small>not resolved or rejected</small></article>
      <article><span>CRITICAL PRIORITY</span><strong>{criticalCount}</strong><small>heuristic score ≥ 81</small></article>
      <article><span>POSSIBLE DUPLICATES</span><strong>{duplicateCount}</strong><small>flagged, never removed</small></article>
    </section>
    <section className="reports-workspace">
      <article className="panel reports-panel"><div className="panel-heading panel-heading-table"><div><p className="eyebrow">LOCAL REPORT STORE</p><h3>Incoming reports</h3></div><button className="icon-button" type="button" title="Refresh reports" aria-label="Refresh reports" onClick={refresh} disabled={loading}><RefreshCw size={16} /></button></div>
        {loading ? <LoadingState label="Loading local reports" /> : <ReportTable reports={reports} selectedId={selectedReport?.report_id} onSelect={(report) => { setSelectedReportId(report.report_id); setSearchParams({}, { replace: true }) }} />}
      </article>
      <ReportDetails key={selectedReport ? `${selectedReport.report_id}-${selectedReport.status}` : 'empty'} report={selectedReport} busy={busy} onClose={() => { setSelectedReportId(null); setSearchParams({}, { replace: true }) }} onStatusUpdate={changeStatus} onDelete={() => setDeleteConfirm(true)} />
    </section>
    <p className="model-footnote">Priority is a LIFEGRID MVP decision-support heuristic. Duplicate checks only flag possible matches; reports remain stored for human review. Synthetic seeded records are not real incidents.</p>
    {formOpen && <ReportForm onSubmit={submitReport} onClose={() => !busy && setFormOpen(false)} submitting={busy} error={formError} />}
    {deleteConfirm && selectedReport && <div className="modal-backdrop" role="presentation"><section className="confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-report-title"><p className="eyebrow">LOCAL DATA ACTION</p><h3 id="delete-report-title">Delete {selectedReport.report_id}?</h3><p>This explicitly removes the report from the local JSON store. Possible duplicates are never deleted automatically.</p><div className="modal-actions"><button className="button button-secondary" type="button" onClick={() => setDeleteConfirm(false)} disabled={busy}>Cancel</button><button className="button button-danger" type="button" onClick={confirmDelete} disabled={busy}>{busy ? 'DELETING…' : 'DELETE REPORT'}</button></div></section></div>}
  </div>
}