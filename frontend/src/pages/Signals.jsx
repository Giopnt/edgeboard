import { useEffect, useState } from 'react'
import { RefreshCw, Info } from 'lucide-react'
import { getSignals } from '../api/client.js'

const SIGNAL_LABELS = {
  rsi_oversold:         'RSI Oversold',
  rsi_overbought:       'RSI Overbought',
  volume_spike:         'Volume Spike',
  ma_bullish_trend:     'MA Bullish Trend',
  ma_bearish_trend:     'MA Bearish Trend',
  price_momentum:       'Price Momentum',
  sentiment_divergence: 'Sentiment Divergence',
}

const SIGNAL_EXPLAIN = {
  rsi_oversold:         'RSI below 35 — the stock has been sold aggressively. Often precedes a bounce.',
  rsi_overbought:       'RSI above 65 — the stock has been bought aggressively. Often precedes a pullback.',
  volume_spike:         'Today\'s volume is 2+ standard deviations above the 20-day average. Someone is paying attention.',
  ma_bullish_trend:     'Price is above both 20-day and 50-day moving averages — all three are aligned bullish.',
  ma_bearish_trend:     'Price is below both moving averages — all three are aligned bearish.',
  price_momentum:       'Stock has moved more than 4% in the last 5 trading days in one direction.',
  sentiment_divergence: 'News sentiment and price are moving in opposite directions — a potential reversal sign.',
}

function Tooltip({ text }) {
  const [show, setShow] = useState(false)
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', marginLeft: 6 }}
      onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      <Info size={12} style={{ color: 'var(--muted)', cursor: 'help' }} />
      {show && (
        <div style={{
          position: 'absolute', left: 20, top: -4, zIndex: 10, width: 240,
          background: 'var(--surface3)', border: '1px solid var(--border2)',
          borderRadius: 6, padding: '8px 10px', fontSize: 11, color: 'var(--text)',
          lineHeight: 1.5, boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        }}>{text}</div>
      )}
    </span>
  )
}

function StrengthBar({ strength, direction }) {
  const color = direction === 'bullish' ? 'var(--green)' : 'var(--red)'
  const pct = (strength || 0) * 100
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 80, height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
        </div>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)', width: 32 }}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>
        Signal strength — how extreme the reading is (0% = barely triggered, 100% = maximum)
      </div>
    </div>
  )
}

function SignalCard({ result }) {
  const hasBullish = result.bullish_count > 0
  const hasBearish = result.bearish_count > 0
  const borderColor = hasBullish && hasBearish ? 'var(--amber-dim)'
    : hasBullish ? 'var(--green-dim)'
    : hasBearish ? 'var(--red-dim)'
    : 'var(--border)'

  return (
    <div style={{ background: 'var(--surface)', border: `1px solid ${borderColor}`, borderRadius: 10, overflow: 'hidden' }}>
      <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 16, fontWeight: 500 }}>{result.symbol}</span>
          {result.current_price && (
            <span style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--muted2)' }}>${result.current_price.toFixed(2)}</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {result.bullish_count > 0 && <span className="badge badge-bullish">▲ {result.bullish_count} bullish</span>}
          {result.bearish_count > 0 && <span className="badge badge-bearish">▼ {result.bearish_count} bearish</span>}
          {result.signal_count === 0 && <span className="badge badge-neutral">No signals</span>}
        </div>
      </div>

      {result.signals?.length > 0 && (
        <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {result.signals.map((s, i) => (
            <div key={i} style={{
              padding: '12px 14px', background: 'var(--surface2)', borderRadius: 8,
              border: `1px solid ${s.direction === 'bullish' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span className={`badge badge-${s.direction}`}>{s.direction}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
                      {SIGNAL_LABELS[s.signal_type] || s.signal_type}
                    </span>
                    <Tooltip text={SIGNAL_EXPLAIN[s.signal_type] || ''} />
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted2)', lineHeight: 1.5 }}>{s.description}</div>
                </div>
                <div style={{ flexShrink: 0, minWidth: 130 }}>
                  <StrengthBar strength={s.strength} direction={s.direction} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border)', fontSize: 11, color: 'var(--muted2)', display: 'flex', justifyContent: 'space-between' }}>
        <span>{result.summary}</span>
        {result.as_of && <span style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>as of {result.as_of}</span>}
      </div>
    </div>
  )
}

export default function Signals() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const load = () => {
    setLoading(true)
    getSignals().then(setData).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const results = data?.results || []
  const filtered = filter === 'all' ? results
    : filter === 'bullish' ? results.filter(r => r.bullish_count > 0)
    : filter === 'bearish' ? results.filter(r => r.bearish_count > 0)
    : results.filter(r => r.signal_count > 0)

  if (loading) return <div className="loading">Scanning signals...</div>

  if (!results.length) return (
    <div className="fade-in">
      <div className="page-header"><h2>Signal Scanner</h2></div>
      <div className="empty">No tickers in watchlist. Add tickers first via the Watchlist page.</div>
    </div>
  )

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Signal Scanner</h2>
        <p>Pattern-based setups across your watchlist — scan on demand, not predictions</p>
      </div>

      {/* Explainer */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, fontSize: 12, color: 'var(--muted2)', lineHeight: 1.6 }}>
        <strong style={{ color: 'var(--text)' }}>How to read this:</strong> Each signal shows a <strong style={{ color: 'var(--text)' }}>direction</strong> (bullish/bearish),
        a <strong style={{ color: 'var(--text)' }}>description</strong> of what's happening technically, and a <strong style={{ color: 'var(--text)' }}>strength bar</strong> showing how extreme the reading is.
        Hover the <Info size={11} style={{ display: 'inline', marginBottom: -2 }} /> icon on any signal type to learn what it means.
        These are <strong style={{ color: 'var(--amber)' }}>observational signals, not buy/sell instructions.</strong>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {['all', 'active', 'bullish', 'bearish'].map(f => (
            <button key={f} className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter(f)}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={12} /> Refresh</button>
      </div>

      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="stat-card"><div className="stat-label">Total Signals</div><div className="stat-value amber">{data.total_signals}</div></div>
        <div className="stat-card"><div className="stat-label">Bullish</div><div className="stat-value bullish">{results.reduce((a, r) => a + r.bullish_count, 0)}</div></div>
        <div className="stat-card"><div className="stat-label">Bearish</div><div className="stat-value bearish">{results.reduce((a, r) => a + r.bearish_count, 0)}</div></div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {filtered.length === 0
          ? <div className="empty">No signals match this filter.</div>
          : filtered.map(r => <SignalCard key={r.symbol} result={r} />)
        }
      </div>

      <div className="disclaimer">⚠ Pattern-based signals only. Not financial advice. Always do your own research before making any trade.</div>
    </div>
  )
}
