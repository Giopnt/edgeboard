import { useEffect, useState } from 'react'
import { RefreshCw, Globe, BookMarked } from 'lucide-react'
import { getMarketRadar, getWatchlistRadar } from '../api/client.js'

const PRIORITY_CONFIG = {
  high:   { label: 'High Priority',  color: 'var(--amber)',  border: 'rgba(245,158,11,0.3)',  bg: 'rgba(245,158,11,0.04)' },
  medium: { label: 'Worth Watching', color: 'var(--blue)',   border: 'rgba(59,130,246,0.2)',  bg: 'rgba(59,130,246,0.03)' },
  low:    { label: 'On The Radar',   color: 'var(--muted2)', border: 'var(--border)',          bg: 'var(--surface)' },
}

function RadarCard({ insight }) {
  const cfg = PRIORITY_CONFIG[insight.priority] || PRIORITY_CONFIG.medium
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, borderRadius: 10, overflow: 'hidden' }}>
      <div style={{ padding: '18px 20px' }}>

        {/* Header row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 17, fontWeight: 600 }}>{insight.symbol}</span>
              {insight.current_price && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--muted2)' }}>
                  ${insight.current_price.toFixed(2)}
                </span>
              )}
              <span style={{
                fontSize: 9, fontFamily: 'var(--mono)', padding: '3px 8px', borderRadius: 4,
                border: `1px solid ${cfg.border}`, color: cfg.color, letterSpacing: '0.08em',
              }}>
                {cfg.label.toUpperCase()}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              {insight.name && (
                <span style={{ fontSize: 12, color: 'var(--muted2)' }}>{insight.name}</span>
              )}
              {insight.sector && (
                <span className="badge badge-neutral" style={{ fontSize: 10 }}>{insight.sector}</span>
              )}
              {insight.tags?.map((tag, i) => (
                <span key={i} style={{
                  fontSize: 10, padding: '2px 8px', borderRadius: 4,
                  background: 'var(--surface3)', color: 'var(--muted2)',
                  border: '1px solid var(--border)',
                }}>{tag}</span>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            {insight.bullish_signals > 0 && <span className="badge badge-bullish">▲ {insight.bullish_signals}</span>}
            {insight.bearish_signals > 0 && <span className="badge badge-bearish">▼ {insight.bearish_signals}</span>}
          </div>
        </div>

        {/* Expert insight text */}
        <div style={{
          fontSize: 13, color: 'var(--text)', lineHeight: 1.7,
          padding: '12px 16px', background: 'rgba(0,0,0,0.2)',
          borderRadius: 6, borderLeft: `3px solid ${cfg.color}`,
        }}>
          {insight.insight}
        </div>

        {/* Raw signals toggle */}
        {insight.raw_signals?.length > 0 && (
          <>
            <button className="btn btn-ghost btn-sm" style={{ marginTop: 10, fontSize: 11 }}
              onClick={() => setExpanded(!expanded)}>
              {expanded ? '▲ Hide' : '▼ Show'} technical signals ({insight.raw_signals.length})
            </button>

            {expanded && (
              <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {insight.raw_signals.map((s, i) => (
                  <div key={i} style={{
                    padding: '8px 12px', background: 'var(--surface2)', borderRadius: 6,
                    border: '1px solid var(--border)', fontSize: 12, color: 'var(--muted2)', lineHeight: 1.5,
                  }}>
                    <span className={`badge badge-${s.direction}`} style={{ marginRight: 8 }}>{s.direction}</span>
                    {s.description}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {insight.as_of && (
        <div style={{ padding: '6px 20px', borderTop: '1px solid var(--border)', fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>
          Data as of {insight.as_of}
        </div>
      )}
    </div>
  )
}

export default function MarketRadar() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState('live')  // 'live' | 'watchlist'
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState(null)

  const load = (m = mode) => {
    setLoading(true)
    setError(null)
    const fn = m === 'live' ? getMarketRadar : getWatchlistRadar
    fn()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(mode) }, [mode])

  const insights = data?.insights || []
  const filtered = filter === 'all'     ? insights
    : filter === 'high'                 ? insights.filter(i => i.priority === 'high')
    : filter === 'bullish'              ? insights.filter(i => i.bullish_signals > i.bearish_signals)
    : insights.filter(i => i.bearish_signals > i.bullish_signals)

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Market Radar</h2>
        <p>Pattern-based intelligence</p>
      </div>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <button
          className={`btn ${mode === 'live' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setMode('live')}
        >
          <Globe size={14} /> Market-Wide (25 stocks)
        </button>
        <button
          className={`btn ${mode === 'watchlist' ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setMode('watchlist')}
        >
          <BookMarked size={14} /> My Watchlist Only
        </button>
      </div>

      {/* How it works */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '12px 16px', marginBottom: 20,
        fontSize: 12, color: 'var(--muted2)', lineHeight: 1.7,
      }}>
        {mode === 'live' ? (
          <>
            <strong style={{ color: 'var(--text)' }}>Market-Wide Radar</strong> scans 25 popular stocks across tech, finance, energy, and healthcare
            using live price data — <strong style={{ color: 'var(--text)' }}>no watchlist needed</strong>.
            It detects RSI extremes, volume spikes, moving average trends, and momentum shifts,
            then translates them into plain language. Takes ~5-10 seconds to load.
            Results show only stocks where something technically interesting is happening right now.
          </>
        ) : (
          <>
            <strong style={{ color: 'var(--text)' }}>Watchlist Radar</strong> scans only the tickers you've personally added and fetched prices for.
            Make sure you've clicked <strong style={{ color: 'var(--text)' }}>Refresh</strong> on your watchlist tickers first.
          </>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <div className="loading" style={{ padding: 0, marginBottom: 12 }}>
            {mode === 'live' ? 'Scanning 25 stocks via live market data...' : 'Scanning watchlist...'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>
            {mode === 'live' ? 'Fetching 6 months of price data and running signal detection' : 'Running signal detectors'}
          </div>
        </div>
      ) : error ? (
        <div>
          <div className="alert alert-red">{error}</div>
          <button className="btn btn-ghost" onClick={() => load(mode)} style={{ marginTop: 10 }}>Retry</button>
        </div>
      ) : !insights.length ? (
        <div className="card">
          <div className="empty" style={{ padding: 40 }}>
            {data?.message || 'No signals detected right now across tracked stocks.'}
          </div>
        </div>
      ) : (
        <>
          {/* Stats row */}
          <div className="grid-3" style={{ marginBottom: 16 }}>
            <div className="stat-card">
              <div className="stat-label">Scanned</div>
              <div className="stat-value">{data?.scanned ?? 0}</div>
              <div className="stat-sub">stocks analyzed</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">With Signals</div>
              <div className="stat-value amber">{insights.length}</div>
              <div className="stat-sub">worth attention</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">High Priority</div>
              <div className="stat-value" style={{ color: 'var(--amber)' }}>
                {insights.filter(i => i.priority === 'high').length}
              </div>
              <div className="stat-sub">multiple signals aligning</div>
            </div>
          </div>

          {/* Filter + refresh */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              {['all', 'high', 'bullish', 'bearish'].map(f => (
                <button key={f} className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setFilter(f)}>
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => load(mode)}>
              <RefreshCw size={12} /> Refresh
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {filtered.length === 0
              ? <div className="empty">No results for this filter.</div>
              : filtered.map(insight => <RadarCard key={insight.symbol} insight={insight} />)
            }
          </div>
        </>
      )}

      <div className="disclaimer" style={{ marginTop: 20 }}>
        ⚠ Market Radar uses technical pattern recognition only. No fundamental analysis, no earnings forecasts, no macro context.
        These are observations — not recommendations. Always do your own research before making any decision.
      </div>
    </div>
  )
}
