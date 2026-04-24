import { useEffect, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { getRisk, addPosition, closePosition, getTickers } from '../api/client.js'

function fmtUSD(n) {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : '-'}$${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
function fmtPct(n) {
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

export default function Portfolio() {
  const [risk, setRisk] = useState(null)
  const [tickers, setTickers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ symbol: '', shares: '', avg_cost: '', opened_at: new Date().toISOString().slice(0, 10) })
  const [adding, setAdding] = useState(false)
  const [formError, setFormError] = useState('')

  const load = () => {
    setLoading(true); setError(null)
    Promise.all([getRisk().catch(() => null), getTickers().catch(() => ({ tickers: [] }))])
      .then(([r, t]) => { setRisk(r); setTickers(t?.tickers || []) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleAdd = async () => {
    setAdding(true); setFormError('')
    try {
      await addPosition({ symbol: form.symbol.toUpperCase(), shares: parseFloat(form.shares), avg_cost: parseFloat(form.avg_cost), opened_at: new Date(form.opened_at).toISOString() })
      setShowAdd(false); setForm({ symbol: '', shares: '', avg_cost: '', opened_at: new Date().toISOString().slice(0, 10) }); load()
    } catch (e) { setFormError(e.message) }
    finally { setAdding(false) }
  }

  const handleClose = async (id) => {
    if (!confirm('Close this position?')) return
    await closePosition(id).catch(() => {}); load()
  }

  if (loading) return <div className="loading">Loading portfolio...</div>
  if (error) return (
    <div className="fade-in">
      <div className="page-header"><h2>Risk Dashboard</h2></div>
      <div className="alert alert-red">Failed to load: {error}</div>
      <button className="btn btn-ghost" onClick={load} style={{ marginTop: 12 }}>Retry</button>
    </div>
  )

  const positions = risk?.positions || []
  const totalValue = risk?.total_current_value
  const drawdownData = [
    { label: '–5%', amount: risk?.drawdown_5pct || 0 },
    { label: '–10%', amount: risk?.drawdown_10pct || 0 },
    { label: '–20%', amount: risk?.drawdown_20pct || 0 },
  ]
  const concentrationData = positions.filter(p => p.current_value)
    .map(p => ({ symbol: p.symbol, pct: totalValue ? parseFloat(((p.current_value / totalValue) * 100).toFixed(1)) : 0 }))
    .sort((a, b) => b.pct - a.pct)

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Risk Dashboard</h2>
        <p>Live portfolio exposure, concentration, and drawdown scenarios</p>
      </div>

      <div className="grid-4">
        {[
          { label: 'Total Value', value: totalValue != null ? `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—', cls: 'amber' },
          { label: 'Cost Basis', value: risk?.total_cost_basis != null ? `$${risk.total_cost_basis.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—', cls: '' },
          { label: 'Unrealized P&L', value: fmtUSD(risk?.total_unrealized_pnl), cls: (risk?.total_unrealized_pnl || 0) >= 0 ? 'bullish' : 'bearish' },
          { label: 'Total Return', value: fmtPct(risk?.total_unrealized_pnl_pct), cls: (risk?.total_unrealized_pnl_pct || 0) >= 0 ? 'bullish' : 'bearish' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className={`stat-value ${s.cls}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {risk?.warnings?.filter(w => !w.includes('No open')).map((w, i) => (
        <div key={i} className={`alert ${w.includes('🔴') ? 'alert-red' : 'alert-warn'}`} style={{ marginBottom: 10 }}>{w}</div>
      ))}

      {positions.length === 0 && (
        <div className="alert alert-warn" style={{ marginBottom: 20 }}>No open positions yet. Add your first position below.</div>
      )}

      {positions.length > 0 && (
        <div className="grid-2">
          <div className="card">
            <div className="card-title">Portfolio Concentration</div>
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={concentrationData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border)" vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" tick={{ fill: 'var(--muted)', fontSize: 11, fontFamily: 'var(--mono)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--muted)', fontSize: 10, fontFamily: 'var(--mono)' }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                  <Tooltip formatter={v => `${v}%`} contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, fontFamily: 'var(--mono)', fontSize: 11 }} />
                  <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
                    {concentrationData.map((entry, i) => (
                      <Cell key={i} fill={entry.pct >= 40 ? 'var(--red)' : entry.pct >= 25 ? 'var(--amber)' : 'var(--blue)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Drawdown Scenarios — if portfolio drops by</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 4 }}>
              {drawdownData.map(d => (
                <div key={d.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', background: 'var(--surface2)', borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 13 }}>Portfolio drops {d.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted2)', marginTop: 2 }}>Estimated dollar loss</div>
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 18, color: 'var(--red)' }}>
                    -${d.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
              ))}
            </div>
            {risk?.largest_position_pct != null && (
              <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--surface2)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>LARGEST SINGLE POSITION</div>
                <div style={{ fontSize: 20, fontFamily: 'var(--mono)', color: risk.largest_position_pct >= 40 ? 'var(--red)' : 'var(--amber)', marginTop: 4 }}>
                  {risk.largest_position_pct.toFixed(1)}% of portfolio
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div className="card-title" style={{ margin: 0 }}>Open Positions</div>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(!showAdd)}><Plus size={12} /> Add Position</button>
        </div>

        {showAdd && (
          <div style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: 'var(--muted2)', marginBottom: 10 }}>Ticker must be in your watchlist first.</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
              <select className="input" style={{ width: 160 }} value={form.symbol} onChange={e => setForm({ ...form, symbol: e.target.value })}>
                <option value="">Select ticker</option>
                {tickers.map(t => <option key={t.symbol} value={t.symbol}>{t.symbol} — {t.name || ''}</option>)}
              </select>
              <input className="input" placeholder="Shares" type="number" value={form.shares} onChange={e => setForm({ ...form, shares: e.target.value })} style={{ width: 110 }} />
              <input className="input" placeholder="Avg cost ($)" type="number" value={form.avg_cost} onChange={e => setForm({ ...form, avg_cost: e.target.value })} style={{ width: 130 }} />
              <input className="input" type="date" value={form.opened_at} onChange={e => setForm({ ...form, opened_at: e.target.value })} style={{ width: 150 }} />
              <button className="btn btn-primary btn-sm" onClick={handleAdd} disabled={adding || !form.symbol}>{adding ? 'Adding...' : 'Save'}</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowAdd(false)}>Cancel</button>
            </div>
            {formError && <div style={{ color: 'var(--red)', fontSize: 12 }}>{formError}</div>}
          </div>
        )}

        {positions.length === 0 ? (
          <div className="empty">No open positions. Add one above.</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Symbol</th><th>Shares</th><th>Avg Cost</th><th>Cost Basis</th><th>Current Price</th><th>Value</th><th>P&L</th><th>Return</th><th></th></tr>
            </thead>
            <tbody>
              {positions.map(p => (
                <tr key={p.id}>
                  <td><span style={{ fontFamily: 'var(--mono)', fontWeight: 500 }}>{p.symbol}</span></td>
                  <td className="mono">{p.shares}</td>
                  <td className="mono">${p.avg_cost?.toFixed(2)}</td>
                  <td className="mono">${p.cost_basis?.toFixed(2)}</td>
                  <td className="mono">{p.current_price ? `$${p.current_price.toFixed(2)}` : '—'}</td>
                  <td className="mono">{p.current_value ? `$${p.current_value.toFixed(2)}` : '—'}</td>
                  <td className={`mono ${(p.unrealized_pnl || 0) >= 0 ? 'bullish' : 'bearish'}`}>{p.unrealized_pnl != null ? fmtUSD(p.unrealized_pnl) : '—'}</td>
                  <td className={`mono ${(p.unrealized_pnl_pct || 0) >= 0 ? 'bullish' : 'bearish'}`}>{fmtPct(p.unrealized_pnl_pct)}</td>
                  <td><button className="btn btn-ghost btn-sm" style={{ color: 'var(--muted2)' }} onClick={() => handleClose(p.id)} title="Close position"><X size={12} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
