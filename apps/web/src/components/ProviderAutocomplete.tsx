import { useEffect, useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { get, queryString } from '../api/client'
import { universePageSchema } from '../api/nse-market'

export function ProviderAutocomplete() {
  const [value,setValue]=useState('');const [term,setTerm]=useState('');const id=useId();const root=useRef<HTMLDivElement>(null);const navigate=useNavigate()
  useEffect(()=>{const timer=setTimeout(()=>setTerm(value.trim()),300);return()=>clearTimeout(timer)},[value])
  const query=useQuery({queryKey:['provider-autocomplete',term],enabled:term.length>=2&&value.trim().length>=2,retry:false,gcTime:600_000,staleTime:600_000,refetchOnWindowFocus:false,refetchOnReconnect:false,queryFn:({signal})=>get(`/nse-market/universe?${queryString({q:term,page_size:8})}`,universePageSchema,signal)})
  const open=value.trim().length>=2
  return <div className="stock-search provider-autocomplete" ref={root}><label className="sr-only" htmlFor={id}>Global NSE and BSE stock search</label><Search size={16}/><input id={id} placeholder="Search NSE and BSE equities" value={value} aria-controls={id+'-results'} aria-expanded={open} role="combobox" aria-autocomplete="list" onChange={e=>setValue(e.target.value)} onKeyDown={e=>{if(e.key==='Escape')setValue('');if(e.key==='ArrowDown'){e.preventDefault();root.current?.querySelector<HTMLButtonElement>('button')?.focus()}}}/>{open&&<div className="search-popover" id={id+'-results'} role="listbox" aria-label="Dated NSE and BSE search results">{query.isFetching&&<p className="caption">Verifying current identities…</p>}{query.error&&<p className="caption">Current instrument search unavailable. Use independent archive search in Market Explorer.</p>}{query.data?.data.rows.map(i=><button key={i.instrument_key} role="option" aria-selected={false} onClick={()=>{setValue('');navigate('/stocks/'+encodeURIComponent('upstox:'+i.instrument_key))}}><strong>{i.symbol}</strong><span>{i.name} · {String(i.segment ?? i.instrument_key.split('|')[0])} · {i.isin}</span></button>)}{query.data&&!query.data.data.rows.length&&<p className="caption">No verified dated equity identity matches.</p>}</div>}</div>
}
