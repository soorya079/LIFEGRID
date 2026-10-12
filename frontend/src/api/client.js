const API_BASE_URL = (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
const STATUS_MESSAGES = {
  400: 'The request could not be accepted. Check the submitted values.',
  401: 'Authentication is required for this request.',
  403: 'You do not have permission to perform this request.',
  404: 'The requested backend endpoint was not found.',
  409: 'The request conflicts with the current report or inventory state. Refresh and try again.',
  422: 'Some submitted values are invalid. Review the highlighted fields.',
  500: 'The backend encountered an internal error. Try again shortly.',
}

export class ApiError extends Error {
  constructor(message, status = 0, code = 'API_ERROR', details = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    })
  } catch {
    console.error(`[LIFEGRID] Network error: Could not reach API at ${API_BASE_URL}`)
    throw new ApiError('Backend service is temporarily unavailable. Please try again in a moment.', 0, 'NETWORK_ERROR')
  }

  let payload
  try { payload = await response.json() } catch { payload = null }
  if (!response.ok || payload?.success === false) {
    const backendError = payload?.error
    throw new ApiError(
      backendError?.message || STATUS_MESSAGES[response.status] || `Request failed (${response.status}).`,
      response.status,
      backendError?.code || 'API_ERROR',
      backendError?.details || [],
    )
  }
  return payload?.data
}

export const getHealth = () => request('/health')
export const getZones = () => request('/api/v1/zones')
export const analyzeRisk = (inputs) => request('/api/v1/risk/analyze', { method: 'POST', body: JSON.stringify(inputs) })
export const simulateFlood = (inputs) => request('/api/v1/simulation/flood', { method: 'POST', body: JSON.stringify(inputs) })
export const getReports = () => request('/api/v1/reports')
export const getReport = (reportId) => request(`/api/v1/reports/${encodeURIComponent(reportId)}`)
export const createReport = (report) => request('/api/v1/reports', { method: 'POST', body: JSON.stringify(report) })
export const updateReportStatus = (reportId, update) => request(`/api/v1/reports/${encodeURIComponent(reportId)}/status`, { method: 'PATCH', body: JSON.stringify(update) })
export const deleteReport = (reportId) => request(`/api/v1/reports/${encodeURIComponent(reportId)}`, { method: 'DELETE' })
export const getResources = () => request('/api/v1/resources')
export const getResourceSummary = () => request('/api/v1/resources/summary')
export const getResourceShortages = () => request('/api/v1/resources/shortages')
export const matchResources = (incident) => request('/api/v1/resources/match', { method: 'POST', body: JSON.stringify(incident) })
export const allocateResource = (allocation) => request('/api/v1/resources/allocate', { method: 'POST', body: JSON.stringify(allocation) })
export const getAllocations = () => request('/api/v1/resources/allocations')

export async function getZoneAssessments() {
  const zoneResponse = await getZones()
  const zones = await Promise.all(zoneResponse.zones.map(async (zone) => {
    const riskInputs = {
      rainfall_mm: zone.rainfall_mm,
      river_level: zone.river_level,
      population_density: zone.population_density,
      road_accessibility: zone.road_accessibility,
      shelter_capacity: zone.shelter_capacity,
      medical_capacity: zone.medical_capacity,
      historical_risk: zone.historical_risk,
    }
    const [risk, simulation] = await Promise.all([
      analyzeRisk(riskInputs),
      simulateFlood({ ...riskInputs, total_population: zone.population }),
    ])
    return { ...zone, risk, simulation }
  }))
  return { dataLabel: zoneResponse.data_label, zones }
}