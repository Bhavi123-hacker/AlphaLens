import { useEffect, useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { get, personalPost, queryString } from '../api/client'
import { jsonObject } from '../api/contracts'
import { masterSchema } from '../api/terminal'

export function ProviderAutocomplete() {
  const [value,setValue]=useState('');const [term,setTerm]=useState('');const id=useId();const root=useRef<HTMLDivElement>(null);const navigate=useNavigate()
  useEffect(()=>{const timer=setTimeout(()=>setTerm(value.trim()),300);return()=>clearTimeout(timer)},[value])
  const query=useQuery({queryKey:['provider-autocomplete',term],enabled:term.length>=2&&value.trim().length>=2,retry:false,gcTime:600_000,staleTime:600_000,refetchOnWindowFocus:false,refetchOnReconnect:false,queryFn:({signal})=>get(`/providers/upstox-private/instruments?${queryString({q:term,limit:8})}`,masterSchema,signal)})
  const open=value.trim().length>=2
  return <div className="stock-search provider-autocomplete" ref={root}><label className="sr-only" htmlFor={id}>Global NSE stock search</label><Search size={16}/><input id={id} placeholder="Search all NSE equities" value={value} aria-controls={id+'-results'} aria-expanded={open} role="combobox" aria-autocomplete="list" onChange={e=>setValue(e.target.value)} onKeyDown={e=>{if(e.key==='Escape')setValue('');if(e.key==='ArrowDown'){e.preventDefault();root.current?.querySelector<HTMLButtonElement>('button')?.focus()}}}/>{open&&<div className="search-popover" id={id+'-results'} role="listbox" aria-label="Current NSE search results">{query.isFetching&&<p className="caption">Verifying current identities…</p>}{query.error&&<p className="caption">Current instrument search unavailable. Use independent archive search in Market Explorer.</p>}{query.data?.data.instruments.map(i=><button key={i.provider_key} role="option" aria-selected={false} onClick={()=>{setValue('');void personalPost('/personal/recent',jsonObject,{instrument_key:i.provider_key}).catch(()=>{});navigate('/stocks/'+encodeURIComponent(i.canonical_security_id||'upstox:'+i.provider_key))}}><strong>{i.symbol}</strong><span>{i.name} · NSE_EQ · {i.isin}</span></button>)}{query.data&&!query.data.data.instruments.length&&<p className="caption">No verified current NSE identity matches.</p>}</div>}</div>
}
