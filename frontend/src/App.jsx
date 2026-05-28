import './index.css'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import RunTrials from './pages/RunTrials.jsx'
import ViewResults from './pages/ViewResults.jsx'
import EntryDetailPage from './pages/EntryDetailPage.jsx'

export default function App() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/run" replace />} />
          <Route path="/run" element={<RunTrials />} />
          <Route path="/results" element={<ViewResults />} />
          <Route path="/results/:filename/:index" element={<EntryDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}
