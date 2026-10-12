import { BrainCircuit, Activity, Grid2X2, GitCompareArrows, Filter, Bell, ChartCandlestick, FlaskConical, Gauge, Layers3, ScanSearch, Settings2, ShieldCheck, Wallet, Sparkles } from 'lucide-react'
export const navigation = [
  ['/', 'Overview', Gauge], ['/market', 'Market Explorer', ScanSearch], ['/analysis', 'Stock Analysis', ChartCandlestick],
  ['/heatmap', 'Market Map', Grid2X2], ['/screener', 'Advanced Screener', Filter], ['/compare', 'Stock Comparison', GitCompareArrows],
  ['/research', 'ML Research Lab', FlaskConical], ['/intelligence', 'Research Intelligence', BrainCircuit], ['/opportunities', 'Opportunities & Signals', Sparkles],
  ['/portfolios', 'Portfolio Analytics', Wallet], ['/paper', 'Paper Trading', Layers3], ['/backtests', 'Backtesting', Activity],
  ['/data-health', 'Data Health', ShieldCheck], ['/notifications', 'Notifications', Bell], ['/settings', 'Settings', Settings2],
] as const
