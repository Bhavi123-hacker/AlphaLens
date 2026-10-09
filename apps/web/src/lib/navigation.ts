import { Activity, ChartCandlestick, FlaskConical, Gauge, Layers3, ScanSearch, Settings2, ShieldCheck, Wallet, Sparkles } from 'lucide-react'
export const navigation = [
  ['/', 'Overview', Gauge], ['/market', 'Market Explorer', ScanSearch], ['/analysis', 'Stock Analysis', ChartCandlestick],
  ['/research', 'ML Research Lab', FlaskConical], ['/opportunities', 'Opportunities & Signals', Sparkles],
  ['/portfolios', 'Portfolio Analytics', Wallet], ['/paper', 'Paper Trading', Layers3], ['/backtests', 'Backtesting', Activity],
  ['/data-health', 'Data Health', ShieldCheck], ['/settings', 'Settings', Settings2],
] as const
