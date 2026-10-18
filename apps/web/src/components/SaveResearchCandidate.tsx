import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { personalPost } from '../api/client'
import { jsonObject } from '../api/contracts'
import { usePersonal } from '../api/personal-hooks'
import { strings } from './researchFormat'

export function SaveResearchCandidate({ instrumentKey }: { instrumentKey: string }) {
  const id = useId()
  const [selected, setSelected] = useState('')
  const [open, setOpen] = useState(false)
  return <details className="candidate-save" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Save to a watchlist</summary>
    {open && <WatchlistChoice key={instrumentKey} instrumentKey={instrumentKey} id={id} selected={selected} choose={setSelected} />}
  </details>
}

function WatchlistChoice({ instrumentKey, id, selected, choose }: { instrumentKey: string; id: string; selected: string; choose: (id: string) => void }) {
  const workspace = usePersonal()
  const cache = useQueryClient()
  const lists = workspace.data?.data.watchlists ?? []
  const list = lists.find(row => row.id === selected) ?? lists[0]
  const keys = strings(list?.value.instrument_keys)
  const already = keys.includes(instrumentKey)
  const save = useMutation({
    mutationFn: () => {
      if (!list || already || keys.length >= 50 || !workspace.data?.data.mutations_enabled) throw new Error('Select an editable watchlist with room for this identity.')
      return personalPost('/personal/records/watchlists', jsonObject, {
        id: list.id, revision: list.revision,
        value: { name: list.value.name, instrument_keys: [...keys, instrumentKey] },
      })
    },
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ['personal-workspace'] })
      await cache.invalidateQueries({ queryKey: ['nse-market-research'] })
    },
    onError: () => cache.invalidateQueries({ queryKey: ['personal-workspace'] }),
  })
  if (workspace.isPending) return <p role="status">Reading your private watchlists…</p>
  if (workspace.isError) return <p role="alert">Watchlists unavailable. {workspace.error.message}</p>
  if (!list) return <p><Link to="/watchlists">Create a named watchlist</Link>, then return to save this security. No prices or forecasts are stored in the list.</p>
  return <div className="watchlist-choice">
    <label htmlFor={id}>Existing watchlist</label>
    <select id={id} value={list.id} onChange={event => { choose(event.target.value); save.reset() }}>
      {lists.map(row => <option key={row.id} value={row.id}>{String(row.value.name)}</option>)}
    </select>
    <button className="button small" disabled={already || keys.length >= 50 || !workspace.data?.data.mutations_enabled || save.isPending} onClick={() => save.mutate()}>
      {save.isPending ? 'Saving identity…' : already ? 'Already in this watchlist' : 'Save security identity'}
    </button>
    {keys.length >= 50 && !already && <p>This list has 50 identities. Choose another list.</p>}
    {!workspace.data?.data.mutations_enabled && <p>Private record editing is disabled.</p>}
    {save.isError && <p role="alert">{save.error.message} Reopen this panel to read the latest revision before retrying.</p>}
    {save.isSuccess && <p role="status">Security saved privately. Prices, scores and portfolio transactions were not copied.</p>}
  </div>
}
