import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { getTickers, scanOpportunities, getBestOpportunities, getPastOpportunities } from '../api/client.js'

const TYPE_LABELS = {
  rsi_oversold:   'RSI Oversold',
  rsi_overbought: 'RSI Overbought',
  volume_spike:   'Volume Spike',
  golden_cross:   'Golden Cross',
  death_cross:    'Death Cross',
  big_move:       'Big Move',
}

// "over N days" explanation
const OUTCOME_EXPLAIN = `"Over N days" means: after this signal fired, this is what the stock did over the next N trading days. It's the actual historical outcome — not a prediction.`

function InfoBox({ text }) {
  return (
    <div style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: 6, padding: '8px 12px', fontSize: 11, color: 'var(--muted2)', lineHeight: 1.5, marginBottom: 14 }}>
      ℹ {text}
    </div>
  )
}

function OpportunityRow({ opp }) {
  const positive = (opp.outcome_pct || 0) >= 0
  return (
    <tr>
      <td className="mono" style={{ color: 'var(--muted2)', fontSize: 12 }}>{opp.date}</td>
      <td>
        <div style={{ display: 'flex', gap: 6 }}>
          <span className={`badge badge-${opp.direction}`}>{opp.direction}</span>
          <span className="badge badge-neutral">{TYPE_LABELS[opp.signal_type] || opp.signal_type}</span>
        </div>
      </td>
      <td style={{ maxWidth: 340, fontSize: 12, color: 'var(--muted2)' }}>{opp.description}</td>
      <td>
        <div style={{ width: 50, height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${(opp.strength || 0) * 100}%`, height: '100%', background: opp.direction === 'bullish' ? 'var(--green)' : 'var(--red)', borderRadius: 2 }} />
        </div>
      </td>
      <td>
        {opp.outcome_pct != null ? (
          <div title={OUTCOME_EXPLAIN}>
            <div className={`mono ${positive ? 'bullish' : 'bearish'}`} style={{ fontSize: 14, fontWeight: 500 }}>
              {positive ? '+' : ''}{opp.outcome_pct.toFixed(2)}%
            </div>
            <div style={{ fontSize: 10, color: 'var(--muted2)' }}>
              {opp.outcome_days}d after signal ↑ hover for info
            </div>
          </div>
        ) : <span style={{ color: 'var(--muted)', fontSize: 12 }}>No data</span>}
      </td>
    </tr>
  )
}

export default function Opportunities() {
  const [tickers, setTickers] = useState([])
  const [selected, setSelected] = useState('')
  const [best, setBest] = useState([])
  const [all, setAll] = useState([])
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [topN, setTopN] = useState(5)
  const [dirFilter, setDirFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')

  useEffect(() => {
    getTickers().then(d => {
      const ts = d?.tickers || []
      setTickers(ts)
      if (ts.length > 0) setSelected(ts[0].symbol)
    })
  }, [])

  const loadData = (sym, n = topN) => {
    if (!sym) return
    setLoading(true)
    Promise.all([
      getBestOpportunities(sym, 365, n),
      getPastOpportunities(sym, 365),
    ]).then(([b, a]) => {
      setBest(b?.opportunities || [])
      setAll(a?.opportunities || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { loadData(selected) }, [selected])

  const handleScan = async () => {
    if (!selected) return
    setScanning(true)
    await scanOpportunities(selected, 365).catch(() => {})
    await loadData(selected)
    setScanning(false)
  }

  const handleTopNChange = (n) => {
    setTopN(n)
    loadData(selected, n)
  }

  const filtered = all.filter(o => {
    if (dirFilter !== 'all' && o.direction !== dirFilter) return false
    if (typeFilter !== 'all' && o.signal_type !== typeFilter) return false
    return true
  })
  const allTypes = [...new Set(all.map(o => o.signal_type))]

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Past Opportunities</h2>
        <p>What patterns fired and what actually happened after — 100% historical, no predictions</p>
      </div>

      <InfoBox text={OUTCOME_EXPLAIN} />

      {/* Controls */}
      <div className="card grid-1">
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <select className="input" style={{ width: 160 }} value={selected} onChange={e => setSelected(e.target.value)}>
            {tickers.map(t => <option key={t.symbol} value={t.symbol}>{t.symbol} — {t.name || ''}</option>)}
          </select>
          <button className="btn btn-primary" onClick={handleScan} disabled={scanning || !selected}>
            <Search size={14} /> {scanning ? 'Scanning...' : 'Scan 1 Year'}
          </button>
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--muted2)' }}>
          Scan detects: RSI crossings, volume spikes, golden/death cross, single-day moves &gt;4%
        </div>
      </div>

      {tickers.length === 0 && <div className="empty">No tickers in watchlist. Add tickers first.</div>}

      {/* Top N selector + best opportunities */}
      {all.length > 0 && (
        <div className="card grid-1">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div className="card-title" style={{ margin: 0 }}>Biggest Moves — Top</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {[1, 3, 5, 10].map(n => (
                <button key={n} className={`btn btn-sm ${topN === n ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => handleTopNChange(n)}>{n}</button>
              ))}
            </div>
          </div>

          {loading ? <div className="loading" style={{ padding: 20 }}>Loading...</div> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {best.length === 0
                ? <div className="empty" style={{ padding: 20 }}>No opportunities found. Run a scan first.</div>
                : best.map((opp, i) => {
                  const positive = (opp.outcome_pct || 0) >= 0
                  return (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '14px 16px', background: 'var(--surface2)', borderRadius: 8,
                      border: `1px solid ${positive ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}`,
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
                          <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted2)' }}>{opp.date}</span>
                          <span className={`badge badge-${opp.direction}`}>{opp.direction}</span>
                          <span className="badge badge-neutral">{TYPE_LABELS[opp.signal_type] || opp.signal_type}</span>
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--muted2)' }}>{opp.description}</div>
                      </div>
                      <div style={{ textAlign: 'right', marginLeft: 20, flexShrink: 0 }} title={OUTCOME_EXPLAIN}>
                        <div className={`mono ${positive ? 'bullish' : 'bearish'}`} style={{ fontSize: 22, fontWeight: 500 }}>
                          {positive ? '+' : ''}{opp.outcome_pct?.toFixed(2)}%
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--muted2)' }}>
                          over next {opp.outcome_days} trading days
                        </div>
                      </div>
                    </div>
                  )
                })
              }
            </div>
          )}
        </div>
      )}

      {/* Full table */}
      {all.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
            <div className="card-title" style={{ margin: 0 }}>All Opportunities — {selected} ({all.length})</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {['all', 'bullish', 'bearish'].map(f => (
                <button key={f} className={`btn btn-sm ${dirFilter === f ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setDirFilter(f)}>
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
              <select className="input" style={{ width: 160, padding: '5px 10px', fontSize: 12 }}
                value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
                <option value="all">All types</option>
                {allTypes.map(t => <option key={t} value={t}>{TYPE_LABELS[t] || t}</option>)}
              </select>
            </div>
          </div>

          {loading ? <div className="loading">Loading...</div> : filtered.length === 0
            ? <div className="empty">No opportunities match this filter.</div>
            : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Signal</th>
                    <th>Description</th>
                    <th>Strength</th>
                    <th>Outcome ↑ hover</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((opp, i) => <OpportunityRow key={i} opp={opp} />)}
                </tbody>
              </table>
            )
          }
        </div>
      )}

      <div className="disclaimer">
        ⚠ "Outcome" shows what actually happened after the signal — historical data only. Past patterns do not guarantee future results. Not financial advice.
      </div>
    </div>
  )
}
