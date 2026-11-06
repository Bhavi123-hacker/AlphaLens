import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { get, personalPost } from '../api/client'
import { jsonObject } from '../api/contracts'
import { workspaceSchema, type Profile } from '../api/personal'
import { Panel, QueryState } from './ui'

export function ResearchProfile() {
  const [open, setOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const query = useQuery({
    queryKey: ['personal-workspace'], enabled: open, retry: false,
    queryFn: ({ signal }) => get('/personal/workspace', workspaceSchema, signal),
  })
  return <Panel title="Research budget and risk preferences" subtitle="Private saved constraints used to explain and filter observed candidates">
    <details onToggle={event => setOpen(event.currentTarget.open)}>
      <summary>Review or update my research constraints</summary>
      {open && <QueryState query={query}>{query.data && <ProfileForm
        key={query.data.data.profile.revision}
        profile={query.data.data.profile.value}
        revision={query.data.data.profile.revision}
        enabled={query.data.data.mutations_enabled}
        onSaved={() => setNotice('Preferences saved; research matches refreshed. Model scores retain their saved values.')}
      />}</QueryState>}
    </details>
    {notice && <p role="status">{notice}</p>}
    <p>Risk tolerance is your research preference. It is not a calibrated model risk class. Supported price, volatility and drawdown constraints are evaluated separately.</p>
    <Link to="/preferences">All technical, liquidity, sector and portfolio preferences</Link>
  </Panel>
}

function ProfileForm({ profile, revision, enabled, onSaved }: { profile: Profile; revision: number; enabled: boolean; onSaved:()=>void }) {
  const [form, setForm] = useState(profile)
  const cache = useQueryClient()
  const save = useMutation({
    mutationFn: () => personalPost('/personal/profile', jsonObject, { revision, profile: form }),
    onSuccess: async () => {
      onSaved()
      await cache.invalidateQueries({ queryKey: ['personal-workspace'] })
      await cache.invalidateQueries({ queryKey: ['nse-market-research'] })
      await cache.invalidateQueries({ queryKey: ['stock-research'] })
    },
  })
  return <form className="personal-form" onSubmit={event => { event.preventDefault(); save.mutate() }}>
    <label>Research budget INR<input type="number" min="0.01" step="0.01" placeholder="Optional" value={form.budget_inr ?? ''} onChange={event => setForm({ ...form, budget_inr: event.target.value || null })} /></label>
    <label>Risk tolerance preference<select value={form.risk_tolerance} onChange={event => setForm({ ...form, risk_tolerance: event.target.value as Profile['risk_tolerance'] })}>{['Low', 'Moderate', 'High'].map(value => <option key={value}>{value}</option>)}</select></label>
    <label>Investment horizon preference<select value={form.horizon} onChange={event => setForm({ ...form, horizon: event.target.value as Profile['horizon'] })}>{['Short', 'Medium', 'Long'].map(value => <option key={value}>{value}</option>)}</select></label>
    <label>Maximum observed drawdown %<input type="number" min="0" max="100" step="0.01" value={form.maximum_drawdown_percent} onChange={event => setForm({ ...form, maximum_drawdown_percent: event.target.value })} /></label>
    <label>Maximum daily volatility %<input type="number" min="0.01" step="0.01" placeholder="Optional" value={form.maximum_daily_volatility_percent ?? ''} onChange={event => setForm({ ...form, maximum_daily_volatility_percent: event.target.value || null })} /></label>
    <div className="form-wide"><button className="button" disabled={!enabled || save.isPending}>{save.isPending ? 'Saving constraints' : 'Save research constraints'}</button>
      {!enabled && <p>Saving is unavailable in this workspace. Existing saved preferences can still be inspected.</p>}
      {save.isError && <p role="alert">{save.error.message}</p>}
    </div>
  </form>
}
