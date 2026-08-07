import { NavLink, Route, Routes } from 'react-router-dom'
import { Activity, GitPullRequest } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import ReviewDetail from './pages/ReviewDetail'

const NAV_LINK = ({ isActive }: { isActive: boolean }) =>
  `inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
  }`

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Activity size={20} />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight">Code Review Agent</h1>
            <p className="text-xs text-slate-500">Multi-agent PR review dashboard</p>
          </div>
          <nav className="ml-auto flex items-center gap-1">
            <NavLink to="/" end className={NAV_LINK}>
              <GitPullRequest size={15} />
              Reviews
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs/:runId" element={<ReviewDetail />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  )
}
