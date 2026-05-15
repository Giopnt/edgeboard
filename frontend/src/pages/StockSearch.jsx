import { useState, useEffect, useRef } from 'react'
import { Search, Loader, Globe } from 'lucide-react'
import { searchStocks, scanAnySymbol } from '../api/client.js'

const PRIORITY_CONFIG = {
  high:   { label: 'High Priority',  color: 'var(--amber)',  border: 'rgba(245,158,11,0.3)',  bg: 'rgba(245,158,11,0.04)' },
  medium: { label: 'Worth Watching', color: 'var(--blue)',   border: 'rgba(59,130,246,0.2)',  bg: 'rgba(59,130,246,0.03)' },
  low:    { label: 'Neutral',        color: 'var(--muted2)', border: 'var(--border)',          bg: 'var(--surface)' },
}

const SIGNAL_LABELS = {
  rsi_oversold:         'RSI Oversold',
  rsi_overbought:       'RSI Overbought',
  volume_spike:         'Volume Spike',
  ma_bullish_trend:     'MA Bullish Trend',
  ma_bearish_trend:     'MA Bearish Trend',
  price_momentum:       'Price Momentum',
  sentiment_divergence: 'Sentiment Divergence',
}

const EXCHANGE_TIPS = [
  { suffix: '.L',  label: 'London (LSE)',      example: 'BGEO.L' },
  { suffix: '.DE', label: 'Frankfurt (XETRA)', example: 'SAP.DE' },
  { suffix: '.PA', label: 'Paris (Euronext)',  example: 'MC.PA' },
  { suffix: '.T',  label: 'Tokyo',             example: '7203.T' },
  { suffix: '.NS', label: 'India (NSE)',        example: 'RELIANCE.NS' },
  { suffix: '.HK', label: 'Hong Kong',         example: '0700.HK' },
]

function SignalResult({ result }) {
  if (!result) return null
  const cfg = PRIORITY_CONFIG[result.priority] || PRIORITY_CONFIG.low
  const [expanded, setExpanded] = useState(true)

  if (!result.has_data) {
    return (
      <div className="card" style={{ borderColor: 'var(--red-dim)' }}>
        <div style={{ color: 'var(--red)', fontSize: 13 }}>
          ⚠ {result.error || `No data found for ${result.symbol}`}
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted2)', marginTop: 8 }}>
          Make sure the ticker symbol is correct. For international stocks, include the exchange suffix (e.g. BGEO.L for London).
        </div>
      </div>
    )
  }

  return (
    <div style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, borderRadius: 10, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 20, fontWeight: 600 }}>{result.symbol}</span>
              {result.current_price && (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 14, color: 'var(--muted2)' }}>
                  {result.currency !== 'USD' ? result.currency + ' ' : '$'}{result.current_price.toFixed(2)}
                </span>
              )}
              <span style={{
                fontSize: 9, fontFamily: 'var(--mono)', padding: '3px 8px', borderRadius: 4,
                border: `1px solid ${cfg.border}`, color: cfg.color, letterSpacing: '0.08em',
              }}>
                {cfg.label.toUpperCase()}
              </span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted2)', marginBottom: 4 }}>{result.name}</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {result.sector && result.sector !== '—' && (
                <span className="badge badge-neutral">{result.sector}</span>
              )}
              {result.exchange && (
                <span className="badge badge-neutral">
                  <Globe size={9} style={{ marginRight: 3 }} />{result.exchange}
                </span>
              )}
              {result.tags?.map((t, i) => (
                <span key={i} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, background: 'var(--surface3)', color: 'var(--muted2)', border: '1px solid var(--border)' }}>{t}</span>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            {result.bullish_count > 0 && <span className="badge badge-bullish">▲ {result.bullish_count}</span>}
            {result.bearish_count > 0 && <span className="badge badge-bearish">▼ {result.bearish_count}</span>}
            {result.signal_count === 0 && <span className="badge badge-neutral">No signals</span>}
          </div>
        </div>
      </div>

      {/* Insight */}
      {result.summary && (
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
          <div style={{
            fontSize: 13, color: 'var(--text)', lineHeight: 1.7,
            padding: '12px 16px', background: 'rgba(0,0,0,0.2)',
            borderRadius: 6, borderLeft: `3px solid ${cfg.color}`,
          }}>
            {result.summary}
          </div>
        </div>
      )}

      {/* Raw signals */}
      {result.signals?.length > 0 && (
        <div style={{ padding: '12px 20px' }}>
          <button className="btn btn-ghost btn-sm" style={{ fontSize: 11, marginBottom: 10 }}
            onClick={() => setExpanded(!expanded)}>
            {expanded ? '▲ Hide' : '▼ Show'} technical signals ({result.signals.length})
          </button>
          {expanded && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {result.signals.map((s, i) => (
                <div key={i} style={{
                  padding: '10px 14px', background: 'var(--surface2)', borderRadius: 8,
                  border: `1px solid ${s.direction === 'bullish' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className={`badge badge-${s.direction}`}>{s.direction}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted2)' }}>
                      {SIGNAL_LABELS[s.signal_type] || s.signal_type}
                    </span>
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 60, height: 3, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ width: `${(s.strength || 0) * 100}%`, height: '100%', background: s.direction === 'bullish' ? 'var(--green)' : 'var(--red)', borderRadius: 2 }} />
                      </div>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted2)' }}>
                        {((s.strength || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted2)', lineHeight: 1.5 }}>{s.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {result.as_of && (
        <div style={{ padding: '6px 20px', borderTop: '1px solid var(--border)', fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>
          Data as of {result.as_of} · {result.disclaimer}
        </div>
      )}
    </div>
  )
}

export default function StockSearch() {
  const [query, setQuery]         = useState('')
  const [suggestions, setSuggs]   = useState([])
  const [showDropdown, setShow]   = useState(false)
  const [scanning, setScanning]   = useState(false)
  const [result, setResult]       = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const inputRef = useRef()
  const debounceRef = useRef()

  // Debounced search suggestions
  useEffect(() => {
    if (query.length < 2) { setSuggs([]); setShow(false); return }
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchLoading(true)
      searchStocks(query)
        .then(d => { setSuggs(d.results || []); setShow(true) })
        .catch(() => {})
        .finally(() => setSearchLoading(false))
    }, 400)
  }, [query])

  const runScan = async (symbol) => {
    setShow(false)
    setQuery(symbol)
    setScanning(true)
    setResult(null)
    try {
      const data = await scanAnySymbol(symbol)
      setResult(data)
    } catch (e) {
      setResult({ symbol, has_data: false, error: e.message, signals: [], insight: null })
    } finally {
      setScanning(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && query.trim()) runScan(query.trim())
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Stock Search</h2>
        <p>Search any stock worldwide and get instant signal analysis</p>
      </div>

      {/* Search box */}
      <div className="card grid-1">
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', pointerEvents: 'none' }} />
              <input
                ref={inputRef}
                className="input"
                placeholder="Search by company name or ticker (e.g. Lion Finance, BGEO.L, NVDA, SAP.DE)"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKey}
                onBlur={() => setTimeout(() => setShow(false), 150)}
                style={{ paddingLeft: 36 }}
                autoFocus
              />
              {searchLoading && (
                <Loader size={13} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)', animation: 'spin 1s linear infinite' }} />
              )}
            </div>
            <button className="btn btn-primary" onClick={() => query.trim() && runScan(query.trim())} disabled={scanning || !query.trim()}>
              {scanning ? 'Scanning...' : 'Scan'}
            </button>
          </div>

          {/* Dropdown suggestions */}
          {showDropdown && suggestions.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 30,
              background: 'var(--surface2)', border: '1px solid var(--border2)',
              borderRadius: 8, marginTop: 4, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              overflow: 'hidden',
            }}>
              {suggestions.map((s, i) => (
                <div key={i}
                  onMouseDown={() => runScan(s.symbol)}
                  style={{
                    padding: '10px 16px', cursor: 'pointer', display: 'flex',
                    justifyContent: 'space-between', alignItems: 'center',
                    borderBottom: '1px solid var(--border)',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--surface3)'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}
                >
                  <div>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 500, fontSize: 13 }}>{s.symbol}</span>
                    <span style={{ fontSize: 12, color: 'var(--muted2)', marginLeft: 10 }}>{s.name}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {s.exchange && <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)' }}>{s.exchange}</span>}
                    {s.type && s.type !== 'EQUITY' && <span className="badge badge-neutral" style={{ fontSize: 9 }}>{s.type}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ fontSize: 11, color: 'var(--muted2)', marginTop: 10 }}>
          Press Enter or click Scan to run full signal analysis on any stock.
          Type a company name to search, or enter a ticker directly.
        </div>
      </div>

      {/* International exchange guide */}
      <div className="card grid-1">
        <div className="card-title">International Stocks — Exchange Suffixes</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {EXCHANGE_TIPS.map(e => (
            <div key={e.suffix}
              style={{
                padding: '8px 12px', background: 'var(--surface2)', borderRadius: 8,
                border: '1px solid var(--border)', cursor: 'pointer',
              }}
              onClick={() => { setQuery(e.example); inputRef.current?.focus() }}
              title={`Click to try ${e.example}`}
            >
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--amber)', marginBottom: 2 }}>{e.suffix}</div>
              <div style={{ fontSize: 11, color: 'var(--muted2)' }}>{e.label}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>e.g. {e.example}</div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted2)', marginTop: 8 }}>
          Click any exchange card to try an example, or type your own ticker with the suffix.
        </div>
      </div>

      {/* Scanning state */}
      {scanning && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <div className="loading" style={{ padding: 0, marginBottom: 8 }}>Fetching live data and running signal analysis...</div>
          <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>This takes a few seconds</div>
        </div>
      )}

      {/* Result */}
      {!scanning && result && <SignalResult result={result} />}

      {/* Empty state */}
      {!scanning && !result && (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--muted2)' }}>
          <Globe size={40} style={{ marginBottom: 16, opacity: 0.3 }} />
          <div style={{ fontSize: 14 }}>Search any stock to see live signal analysis</div>
          <div style={{ fontSize: 12, marginTop: 6, color: 'var(--muted)' }}>
            Works for US stocks, London, Frankfurt, Paris, Tokyo, and more
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: translateY(-50%) rotate(0deg); } to { transform: translateY(-50%) rotate(360deg); } }
      `}</style>
    </div>
  )
}
