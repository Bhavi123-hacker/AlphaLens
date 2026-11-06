import { BrainCircuit, Activity, Grid2X2, GitCompareArrows, Filter, Bell, ChartCandlestick, FlaskConical, Gauge, Layers3, ScanSearch, Settings2, ShieldCheck, Wallet, Sparkles, SlidersHorizontal, NotebookPen, List } from 'lucide-react'
export const navigation = [
  ['/', 'Overview', Gauge], ['/nse-market', 'NSE Market & Research', ScanSearch], ['/market', 'Market Explorer', ScanSearch], ['/analysis', 'Stock Analysis', ChartCandlestick],
  ['/heatmap', 'Market Map', Grid2X2], ['/screener', 'Advanced Screener', Filter], ['/compare', 'Stock Comparison', GitCompareArrows],
  ['/watchlists','My Watchlists',List], ['/my-portfolio','My Portfolio',Wallet], ['/preferences','Research Preferences',SlidersHorizontal],
  ['/decision-desk','Research Decision Desk',Sparkles], ['/opportunities', 'Explore Opportunities', Sparkles], ['/experimental-ai', 'Experimental AI Stock Research', BrainCircuit], ['/experimental-ai-v2', 'V2 Predictive Edge Research', BrainCircuit], ['/research', 'ML Research Lab', FlaskConical], ['/intelligence', 'Research Intelligence', BrainCircuit], ['/copilot','Research Copilot',BrainCircuit],
  ['/journal','Research Journal',NotebookPen], ['/research-alerts','Smart Research Alerts',Bell], ['/portfolios', 'Portfolio Analytics', Wallet], ['/paper', 'Paper Trading', Layers3], ['/backtests', 'Backtesting', Activity],
  ['/data-health', 'Data Health', ShieldCheck], ['/notifications', 'Notifications', Bell], ['/settings', 'Settings', Settings2],
] as const
