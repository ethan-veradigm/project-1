import { NavLink } from 'react-router-dom'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>PubMedQA Eval</h2>
        <div className="logo-subtitle">Evaluation Dashboard</div>
      </div>
      <nav className="sidebar-nav">
        <NavLink
          to="/run"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          🚀 Run Trials
        </NavLink>
        <NavLink
          to="/results"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          📊 View Results
        </NavLink>
      </nav>
    </aside>
  )
}
