import { useEffect } from 'react'

export function remainingProviderMemory(value: unknown): number | null {
  const remaining:number[]=[]
  const visit=(item:unknown)=>{if(!item||typeof item!=='object')return;if(Array.isArray(item)){item.forEach(visit);return}for(const [key,field]of Object.entries(item)){if(key==='expires_in_seconds'&&typeof field==='number'&&Number.isFinite(field))remaining.push(Math.max(0,field));else visit(field)}}
  visit(value)
  return remaining.length?Math.min(...remaining):null
}
export function useProviderMemoryExpiry(value:unknown,clear:()=>void) {
  useEffect(()=>{const seconds=remainingProviderMemory(value);if(seconds==null)return;const timer=setTimeout(clear,seconds*1000);return()=>clearTimeout(timer)},[value,clear])
}
