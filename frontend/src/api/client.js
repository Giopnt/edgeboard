const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function del(path) {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.status === 204 ? null : res.json()
}

// Tickers
export const getTickers = () => get('/tickers')
export const addTicker = (symbol, name, sector) =>
  post('/tickers', { symbol, name, sector })
export const deleteTicker = (symbol) => del(`/tickers/${symbol}`)

// Prices
export const getPrices = (symbol, days = 90) =>
  get(`/prices/${symbol}?days=${days}`)
export const fetchPrices = (symbol) =>
  post(`/prices/${symbol}/fetch?days=365`)

// Sentiment
export const getSentimentHistory = (symbol, days = 30) =>
  get(`/sentiment/${symbol}?days=${days}`)
export const getSentimentSummary = (symbol) =>
  get(`/sentiment/${symbol}/summary`)
export const fetchSentiment = (symbol) =>
  post(`/sentiment/${symbol}/fetch?days=7`)

// Portfolio
export const getRisk = () => get('/portfolio/risk')
export const getPositions = () => get('/portfolio/positions')
export const addPosition = (data) => post('/portfolio/positions', data)
export const closePosition = (id) => del(`/portfolio/positions/${id}`)
export const getPortfolioSummary = () => get('/portfolio/summary')

// Signals
export const getSignals = () => get('/signals')
export const getTickerSignals = (symbol) => get(`/signals/${symbol}`)

// Opportunities
export const scanOpportunities = (symbol, days = 365) =>
  post(`/opportunities/${symbol}/scan?days=${days}`)
export const getBestOpportunities = (symbol, days = 90, limit = 5) =>
  get(`/opportunities/${symbol}/best?days=${days}&limit=${limit}`)
export const getPastOpportunities = (symbol, days = 90) =>
  get(`/opportunities/${symbol}/past?days=${days}&limit=100`)
export const getWatchlistOpportunities = () =>
  get('/opportunities/watchlist/summary?days=30')

// Market
export const getPopularStocks = () => get('/market/popular')
export const getMarketRadar = () => get('/market/radar')
export const getWatchlistRadar = () => get('/market/radar/watchlist')