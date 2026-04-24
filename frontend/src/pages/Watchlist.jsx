import { useEffect, useState, useRef } from 'react'
import { Plus, RefreshCw, Trash2, Search } from 'lucide-react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { getTickers, addTicker, deleteTicker, fetchPrices, fetchSentiment, getSentimentSummary, getPrices, getPopularStocks } from '../api/client.js'

const SentimentBar = ({ score }) => {
  const pct = ((score + 1) / 2) * 100
  const color = score > 0.05 ? 'var(--green)' : score < -0.05 ? 'var(--red)' : 'var(--muted2)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color, width: 44, textAlign: 'right' }}>
        {score > 0 ? '+' : ''}{score?.toFixed(3)}
      </span>
    </div>
  )
}

function TickerRow({ ticker, onDelete, onRefresh }) {
  const [sentiment, setSentiment] = useState(null)
  const [prices, setPrices] = useState([])
  const [fetching, setFetching] = useState(false)

  useEffect(() => {
    getSentimentSummary(ticker.symbol).then(setSentiment).catch(() => {})
    getPrices(ticker.symbol, 30).then(data => {
      setPrices(data.map(p => ({ date: p.date.slice(5), close: p.close })))
    }).catch(() => {})
  }, [ticker.symbol])

  const handleRefresh = async () => {
    setFetching(true)
    try {
      await fetchPrices(ticker.symbol)
      await fetchSentiment(ticker.symbol)
      onRefresh()
    } finally { setFetching(false) }
  }

  return (
    <tr>
      <td>
        <div style={{ fontFamily: 'var(--mono)', fontWeight: 500, fontSize: 14 }}>{ticker.symbol}</div>
        <div style={{ fontSize: 11, color: 'var(--muted2)' }}>{ticker.name || '—'}</div>
      </td>
      <td><span style={{ fontSize: 12, color: 'var(--muted2)' }}>{ticker.sector || '—'}</span></td>
      <td style={{ minWidth: 120 }}>
        {prices.length > 0 ? (
          <ResponsiveContainer width="100%" height={40}>
            <LineChart data={prices}>
              <Line type="monotone" dataKey="close" stroke="var(--amber)" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : <span style={{ color: 'var(--muted)', fontSize: 11 }}>No data — click Refresh</span>}
      </td>
      <td style={{ minWidth: 160 }}>
        {sentiment?.latest_score != null ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span className={`badge badge-${sentiment.latest_label === 'bullish' ? 'bullish' : sentiment.latest_label === 'bearish' ? 'bearish' : 'neutral'}`}>
                {sentiment.latest_label}
              </span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>{sentiment.trend}</span>
            </div>
            <SentimentBar score={sentiment.latest_score} />
          </div>
        ) : <span style={{ color: 'var(--muted)', fontSize: 11 }}>No sentiment — click Refresh</span>}
      </td>
      <td>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn btn-ghost btn-sm" onClick={handleRefresh} disabled={fetching}>
            <RefreshCw size={12} /> {fetching ? 'Fetching...' : 'Refresh'}
          </button>
          <button className="btn btn-ghost btn-sm" style={{ color: 'var(--red)', borderColor: 'var(--red-dim)' }}
            onClick={() => onDelete(ticker.symbol)}>
            <Trash2 size={12} />
          </button>
        </div>
      </td>
    </tr>
  )
}

function StockSearch({ onAdd }) {
  const [query, setQuery] = useState('')
  const [popular, setPopular] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [selected, setSelected] = useState(null)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const ref = useRef()

  useEffect(() => {
    getPopularStocks().then(d => setPopular(d.stocks || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!query.trim()) { setSuggestions([]); setShowDropdown(false); return }
    const q = query.toLowerCase()
    const matches = popular.filter(s =>
      s.symbol.toLowerCase().startsWith(q) ||
      s.name.toLowerCase().includes(q)
    ).slice(0, 8)
    setSuggestions(matches)
    setShowDropdown(matches.length > 0)
  }, [query, popular])

  const pick = (stock) => {
    setSelected(stock)
    setQuery(stock.symbol)
    setShowDropdown(false)
  }

  const handleAdd = async () => {
    const sym = (selected?.symbol || query).toUpperCase().trim()
    if (!sym) return
    setAdding(true); setError('')
    try {
      await addTicker(sym, selected?.name, selected?.sector)
      setQuery(''); setSelected(null)
      onAdd()
    } catch (e) { setError(e.message) }
    finally { setAdding(false) }
  }

  return (
    <div>
      <div style={{ position: 'relative', display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', width: 280 }} ref={ref}>
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', pointerEvents: 'none' }} />
            <input
              className="input"
              placeholder="Search by name or ticker (e.g. Apple, NVDA)"
              value={query}
              onChange={e => { setQuery(e.target.value); setSelected(null) }}
              onFocus={() => query && setSuggestions(popular.filter(s => s.symbol.toLowerCase().startsWith(query.toLowerCase()) || s.name.toLowerCase().includes(query.toLowerCase())).slice(0, 8))}
              onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
              style={{ paddingLeft: 32 }}
            />
          </div>
          {showDropdown && suggestions.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20,
              background: 'var(--surface2)', border: '1px solid var(--border2)',
              borderRadius: 8, marginTop: 4, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
              overflow: 'hidden',
            }}>
              {suggestions.map(s => (
                <div key={s.symbol}
                  onMouseDown={() => pick(s)}
                  style={{
                    padding: '9px 14px', cursor: 'pointer', display: 'flex',
                    justifyContent: 'space-between', alignItems: 'center',
                    borderBottom: '1px solid var(--border)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--surface3)'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}
                >
                  <div>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 500, fontSize: 13 }}>{s.symbol}</span>
                    <span style={{ fontSize: 12, color: 'var(--muted2)', marginLeft: 10 }}>{s.name}</span>
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>{s.sector}</span>
                </div>
              ))}
              {query.length >= 2 && suggestions.length === 0 && (
                <div style={{ padding: '10px 14px', fontSize: 12, color: 'var(--muted2)' }}>
                  Not in suggestions? Type the exact ticker symbol and click Add.
                </div>
              )}
            </div>
          )}
        </div>
        <button className="btn btn-primary" onClick={handleAdd} disabled={adding || !query.trim()}>
          <Plus size={14} /> {adding ? 'Adding...' : 'Add to Watchlist'}
        </button>
      </div>
      {error && <div style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>{error}</div>}
      <div style={{ fontSize: 11, color: 'var(--muted2)', marginTop: 8 }}>
        After adding, click <strong>Refresh</strong> on the ticker to fetch its price history and sentiment data.
      </div>
    </div>
  )
}

function PopularSuggestions({ existing, onAdd }) {
  const [popular, setPopular] = useState([])

  useEffect(() => {
    getPopularStocks().then(d => setPopular(d.stocks || [])).catch(() => {})
  }, [])

  const existingSymbols = new Set(existing.map(t => t.symbol))
  const suggestions = popular.filter(s => !existingSymbols.has(s.symbol)).slice(0, 12)

  if (suggestions.length === 0) return null

  return (
    <div className="card grid-1">
      <div className="card-title">Popular Stocks — Quick Add</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {suggestions.map(s => (
          <button key={s.symbol} className="btn btn-ghost btn-sm"
            onClick={() => addTicker(s.symbol, s.name, s.sector).then(onAdd).catch(() => {})}
            title={`${s.name} — ${s.sector}`}
            style={{ fontFamily: 'var(--mono)' }}>
            <Plus size={11} /> {s.symbol}
          </button>
        ))}
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted2)', marginTop: 8 }}>
        Click any ticker to add it instantly. Remember to hit Refresh after to load its data.
      </div>
    </div>
  )
}

export default function Watchlist() {
  const [tickers, setTickers] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    getTickers().then(data => {
      setTickers(data.tickers || [])
      setLoading(false)
    })
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (sym) => {
    if (!confirm(`Remove ${sym} from watchlist?`)) return
    await deleteTicker(sym).catch(() => {})
    load()
  }

  if (loading) return <div className="loading">Loading watchlist...</div>

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Watchlist</h2>
        <p>Search for stocks by name or ticker — then Refresh to load price and sentiment data</p>
      </div>

      <div className="card grid-1">
        <div className="card-title">Add a Stock</div>
        <StockSearch onAdd={load} />
      </div>

      <PopularSuggestions existing={tickers} onAdd={load} />

      <div className="card">
        <div className="card-title">{tickers.length} Tracked Ticker{tickers.length !== 1 ? 's' : ''}</div>
        {tickers.length === 0 ? (
          <div className="empty">No tickers yet. Search for one above or use quick-add buttons.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Sector</th>
                <th style={{ minWidth: 120 }}>30d Price</th>
                <th>Sentiment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tickers.map(t => (
                <TickerRow key={t.symbol} ticker={t} onDelete={handleDelete} onRefresh={load} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
