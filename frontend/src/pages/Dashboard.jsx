import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from 'recharts'
import { getRisk, getSignals, getWatchlistOpportunities, getTickers, getPrices } from '../api/client.js'

// Time range → days mapping
const RANGES = [
  { label: '5D',  days: 5   },
  { label: '1M',  days: 30  },
  { label: '3M',  days: 90  },
  { label: '6M',  days: 180 },
  { label: 'YTD', days: null }, // computed below
  { label: '1Y',  days: 365 },
  { label: '2Y',  days: 730 },
  { label: 'MAX', days: 1825 },
]

function getYTDDays() {
  const now = new Date()
  const jan1 = new Date(now.getFullYear(), 0, 1)
  return Math.ceil((now - jan1) / (1000 * 60 * 60 * 24))
}

function formatDate(dateStr, days) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (days <= 30)  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  if (days <= 365) return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

function fmtUSD(n) {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : '-'}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
function fmtPct(n) {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 6, padding: '8px 12px', fontFamily: 'var(--mono)', fontSize: 11
    }}>
      <div style={{ color: 'var(--muted2)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--amber)' }}>${Number(payload[0].value).toFixed(2)}</div>
    </div>
  )
}

export default function Dashboard() {
  const [risk, setRisk]       = useState(null)
  const [signals, setSignals] = useState(null)
  const [opps, setOpps]       = useState(null)
  const [tickers, setTickers] = useState([])
  const [loading, setLoading] = useState(true)

  // Chart state
  const [selectedSymbol, setSelectedSymbol] = useState(null)
  const [selectedRange, setSelectedRange]   = useState('3M')
  const [prices, setPrices]                 = useState([])
  const [chartLoading, setChartLoading]     = useState(false)
  const [priceChange, setPriceChange]       = useState(null)

  // Load all dashboard data
  useEffect(() => {
    Promise.all([
      getRisk().catch(() => null),
      getSignals().catch(() => null),
      getWatchlistOpportunities().catch(() => null),
      getTickers().catch(() => ({ tickers: [] })),
    ]).then(([r, s, o, t]) => {
      setRisk(r)
      setSignals(s)
      setOpps(o)
      const ts = t?.tickers || []
      setTickers(ts)
      if (ts.length > 0) setSelectedSymbol(ts[0].symbol)
      setLoading(false)
    })
  }, [])

  // Load price data when symbol or range changes
  useEffect(() => {
    if (!selectedSymbol) return
    const range = RANGES.find(r => r.label === selectedRange)
    const days = range?.days ?? getYTDDays()
    setChartLoading(true)
    getPrices(selectedSymbol, Math.min(days, 1825))
      .then(data => {
        const mapped = data.map(p => ({
          date:  formatDate(p.date, days),
          close: p.close,
          raw:   p.date,
        }))
        setPrices(mapped)

        // Compute change over period
        if (mapped.length >= 2) {
          const first = mapped[0].close
          const last  = mapped[mapped.length - 1].close
          const chg   = last - first
          const chgPct = (chg / first) * 100
          setPriceChange({ chg, chgPct })
        } else {
          setPriceChange(null)
        }
      })
      .catch(() => setPrices([]))
      .finally(() => setChartLoading(false))
  }, [selectedSymbol, selectedRange])

  if (loading) return <div className="loading">Loading dashboard...</div>

  const totalSignals   = signals?.total_signals ?? 0
  const bullishSignals = signals?.results?.reduce((a, r) => a + (r.bullish_count || 0), 0) ?? 0
  const bearishSignals = signals?.results?.reduce((a, r) => a + (r.bearish_count || 0), 0) ?? 0
  const pnl            = risk?.total_unrealized_pnl
  const pnlPct         = risk?.total_unrealized_pnl_pct
  const portfolioValue = risk?.total_current_value
  const isPositive     = priceChange ? priceChange.chg >= 0 : true
  const strokeColor    = priceChange ? (isPositive ? 'var(--green)' : 'var(--red)') : 'var(--amber)'
  const gradientId     = isPositive ? 'priceGradGreen' : 'priceGradRed'

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Your market overview</p>
      </div>

      {/* Top stats */}
      <div className="grid-4">
        <div className="stat-card">
          <div className="stat-label">Portfolio Value</div>
          <div className="stat-value amber">
            {portfolioValue != null
              ? `$${portfolioValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
              : '—'}
          </div>
          <div className="stat-sub">{tickers.length} ticker{tickers.length !== 1 ? 's' : ''} tracked</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Unrealized P&L</div>
          <div className={`stat-value ${pnl == null ? '' : pnl >= 0 ? 'bullish' : 'bearish'}`}>
            {pnl != null ? `${pnl >= 0 ? '+' : '-'}$${Math.abs(pnl).toFixed(2)}` : '—'}
          </div>
          <div className="stat-sub">{pnlPct != null ? fmtPct(pnlPct) + ' total return' : 'No positions yet'}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Active Signals</div>
          <div className="stat-value amber">{totalSignals}</div>
          <div className="stat-sub">
            <span className="bullish">{bullishSignals} bullish</span>
            {' · '}
            <span className="bearish">{bearishSignals} bearish</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Watchlist</div>
          <div className="stat-value">{tickers.length}</div>
          <div className="stat-sub" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {tickers.map(t => t.symbol).join(', ') || 'No tickers yet'}
          </div>
        </div>
      </div>

      {/* Price chart */}
      <div className="card grid-1">
        {/* Chart header — ticker switcher + range selector */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>

          {/* Ticker tabs */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {tickers.length === 0 ? (
              <span style={{ color: 'var(--muted2)', fontSize: 12 }}>Add tickers to see charts</span>
            ) : (
              tickers.map(t => (
                <button
                  key={t.symbol}
                  className={`btn btn-sm ${selectedSymbol === t.symbol ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setSelectedSymbol(t.symbol)}
                  style={{ fontFamily: 'var(--mono)' }}
                >
                  {t.symbol}
                </button>
              ))
            )}

            {/* Price change indicator */}
            {priceChange && !chartLoading && (
              <span style={{
                fontFamily: 'var(--mono)', fontSize: 12, marginLeft: 8,
                color: isPositive ? 'var(--green)' : 'var(--red)',
              }}>
                {isPositive ? '+' : ''}{priceChange.chg.toFixed(2)} ({isPositive ? '+' : ''}{priceChange.chgPct.toFixed(2)}%)
              </span>
            )}
          </div>

          {/* Range tabs */}
          <div style={{ display: 'flex', gap: 4 }}>
            {RANGES.map(r => (
              <button
                key={r.label}
                onClick={() => setSelectedRange(r.label)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  padding: '4px 8px', borderRadius: 4,
                  fontFamily: 'var(--mono)', fontSize: 11,
                  color: selectedRange === r.label ? 'var(--amber)' : 'var(--muted)',
                  fontWeight: selectedRange === r.label ? 600 : 400,
                  borderBottom: selectedRange === r.label ? '2px solid var(--amber)' : '2px solid transparent',
                  transition: 'all 0.15s',
                }}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        {chartLoading ? (
          <div className="loading" style={{ height: 280 }}>Loading chart...</div>
        ) : prices.length === 0 ? (
          <div className="empty" style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {selectedSymbol
              ? `No price data for ${selectedSymbol} in this range. Click Refresh in Watchlist first.`
              : 'Add tickers to your watchlist to see charts'}
          </div>
        ) : (
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={prices} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="priceGradGreen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--green)" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="priceGradRed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--red)" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="var(--red)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'var(--muted)', fontSize: 10, fontFamily: 'var(--mono)' }}
                  tickLine={false} axisLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: 'var(--muted)', fontSize: 10, fontFamily: 'var(--mono)' }}
                  tickLine={false} axisLine={false}
                  tickFormatter={v => `$${v}`}
                  domain={['auto', 'auto']}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke={strokeColor}
                  strokeWidth={2}
                  fill={`url(#${gradientId})`}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Bottom row */}
      <div className="grid-2">
        {/* Active signals */}
        {signals?.results?.filter(r => r.signal_count > 0).length > 0 && (
          <div className="card">
            <div className="card-title">Active Signals</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {signals.results.filter(r => r.signal_count > 0).slice(0, 5).map(r => (
                <div key={r.symbol} style={{
                  padding: '10px 12px', background: 'var(--surface2)',
                  borderRadius: 8, border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 500, fontSize: 13 }}>{r.symbol}</span>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {r.bullish_count > 0 && <span className="badge badge-bullish">▲ {r.bullish_count}</span>}
                      {r.bearish_count > 0 && <span className="badge badge-bearish">▼ {r.bearish_count}</span>}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted2)' }}>{r.summary}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Risk warnings */}
        {risk?.warnings?.filter(w => !w.includes('No open')).length > 0 && (
          <div className="card">
            <div className="card-title">Risk Warnings</div>
            {risk.warnings.filter(w => !w.includes('No open')).map((w, i) => (
              <div key={i} className={`alert ${w.includes('🔴') ? 'alert-red' : 'alert-warn'}`}>{w}</div>
            ))}
          </div>
        )}

        {/* Best recent opportunity */}
        {opps?.summary?.length > 0 && opps.summary[0]?.best_opportunity && (() => {
          const best = opps.summary[0]
          const opp  = best.best_opportunity
          return (
            <div className="card">
              <div className="card-title">Biggest Recent Opportunity (30d)</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 15, fontWeight: 500 }}>{best.symbol}</span>
                    <span className={`badge badge-${opp.direction}`}>{opp.direction}</span>
                    <span className="badge badge-neutral">{opp.signal_type?.replace(/_/g, ' ')}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted2)', maxWidth: 360 }}>{opp.description}</div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 20 }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 22, fontWeight: 500 }}
                    className={opp.outcome_pct >= 0 ? 'bullish' : 'bearish'}>
                    {opp.outcome_pct >= 0 ? '+' : ''}{opp.outcome_pct?.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--muted2)' }}>over {opp.outcome_days}d</div>
                </div>
              </div>
            </div>
          )
        })()}
      </div>
    </div>
  )
}
