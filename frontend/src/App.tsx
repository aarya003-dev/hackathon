import { Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Pipeline from './pages/Pipeline'
import MetricsPage from './pages/MetricsPage'
import ReviewDetail from './pages/ReviewDetail'
import ReviewSummary from './pages/ReviewSummary'
import Agents from './pages/Agents'

export default function App() {
  return (
    <div className="min-h-screen bg-surface text-slate-200">
      <Sidebar />
      <main className="pl-60">
        <div className="mx-auto max-w-6xl px-6 py-6">
          <Routes>
            <Route path="/" element={<Pipeline />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="/runs/:runId" element={<ReviewDetail />} />
            <Route path="/runs/:runId/summary" element={<ReviewSummary />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
