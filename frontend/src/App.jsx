import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { getHealth } from './api/client'
import Header from './components/Header'
import LoadingState from './components/LoadingState'
import Sidebar from './components/Sidebar'

const Analytics = lazy(() => import('./pages/Analytics'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Reports = lazy(() => import('./pages/Reports'))
const Resources = lazy(() => import('./pages/Resources'))
const RiskMap = lazy(() => import('./pages/RiskMap'))
const Simulation = lazy(() => import('./pages/Simulation'))

function OperationsApp() {
  const [navigationOpen, setNavigationOpen] = useState(false)
  const [apiStatus, setApiStatus] = useState('checking')

  useEffect(() => {
    let active = true
    getHealth()
      .then(() => active && setApiStatus('connected'))
      .catch(() => active && setApiStatus('offline'))
    return () => { active = false }
  }, [])

  return (
    <div className="app-frame">
      <Sidebar open={navigationOpen} onNavigate={() => setNavigationOpen(false)} />
      {navigationOpen && <button className="nav-backdrop" type="button" aria-label="Close navigation" onClick={() => setNavigationOpen(false)} />}
      <div className="workspace">
        <Header apiStatus={apiStatus} onMenuClick={() => setNavigationOpen((open) => !open)} />
        <main className="page-content" id="main-content">
          <Suspense fallback={<LoadingState label="Opening operations view" />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/map" element={<RiskMap />} />
              <Route path="/simulation" element={<Simulation />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/resources" element={<Resources />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
        <footer className="workspace-footer">
          <span>LIFEGRID LOCAL OPERATIONS WORKSPACE</span>
          <span>DECISION SUPPORT ONLY · VERIFY WITH OFFICIAL SOURCES</span>
        </footer>
      </div>
    </div>
  )
}

export default function App() {
  return <BrowserRouter><OperationsApp /></BrowserRouter>
}
