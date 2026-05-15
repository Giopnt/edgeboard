import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, ListPlus, ShieldAlert, Zap, History, Radio, Search } from 'lucide-react'
import Dashboard     from './pages/Dashboard.jsx'
import Portfolio     from './pages/Portfolio.jsx'
import Signals       from './pages/Signals.jsx'
import Opportunities from './pages/Opportunities.jsx'
import Watchlist     from './pages/Watchlist.jsx'
import MarketRadar   from './pages/MarketRadar.jsx'
import StockSearch   from './pages/StockSearch.jsx'

const NAV = [
  { to: '/',              icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/search',        icon: Search,          label: 'Stock Search' },
  { to: '/watchlist',     icon: ListPlus,        label: 'Watchlist' },
  { to: '/portfolio',     icon: ShieldAlert,     label: 'Risk' },
  { to: '/signals',       icon: Zap,             label: 'Signals' },
  { to: '/opportunities', icon: History,         label: 'Opportunities' },
  { to: '/radar',         icon: Radio,           label: 'Market Radar' },
]

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>Edge<span>Board</span></h1>
          <p>Market Intelligence</p>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section">Navigation</div>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <Icon /> {label}
            </NavLink>
          ))}
        </nav>
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', lineHeight: 1.6 }}>
            ⚠ Pattern-based signals.<br />Not financial advice.
          </div>
        </div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/"              element={<Dashboard />} />
          <Route path="/search"        element={<StockSearch />} />
          <Route path="/watchlist"     element={<Watchlist />} />
          <Route path="/portfolio"     element={<Portfolio />} />
          <Route path="/signals"       element={<Signals />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/radar"         element={<MarketRadar />} />
        </Routes>
      </main>
    </div>
  )
}
