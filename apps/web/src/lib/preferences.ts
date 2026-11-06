import { useSyncExternalStore } from 'react'
export type Favorite = { security_id: string; symbol: string; name: string }
type Preferences = { theme: 'dark' | 'light'; compact: boolean; favorites: Favorite[] }
const defaults: Preferences = { theme: 'dark', compact: false, favorites: [] }
let cached: Preferences | undefined
const listeners = new Set<() => void>()
function read(): Preferences {
  if (cached) return cached
  try {
    const raw: unknown = JSON.parse(localStorage.getItem('alphalens.preferences.v1') ?? 'null')
    if (raw && typeof raw === 'object' && 'favorites' in raw && Array.isArray(raw.favorites)) {
      const value = raw as Partial<Preferences>
      cached = { theme: value.theme === 'light' ? 'light' : 'dark', compact: value.compact === true,
        favorites: raw.favorites.filter((f): f is Favorite => typeof f === 'object' && f !== null && typeof f.security_id === 'string' && typeof f.symbol === 'string' && typeof f.name === 'string').slice(0, 100) }
    }
  } catch { /* Browser storage is optional; no financial records are stored here. */ }
  return cached ?? (cached = defaults)
}
export function setPreferences(update: Partial<Preferences>) {
  cached = { ...read(), ...update }
  try { localStorage.setItem('alphalens.preferences.v1', JSON.stringify(cached)) } catch { /* Preference remains session-local when storage is blocked. */ }
  listeners.forEach((listener) => listener())
}
export function usePreferences() { return useSyncExternalStore((listener) => { listeners.add(listener); return () => listeners.delete(listener) }, read) }
export function toggleFavorite(favorite: Favorite) {
  const favorites = read().favorites
  setPreferences({ favorites: favorites.some((f) => f.security_id === favorite.security_id)
    ? favorites.filter((f) => f.security_id !== favorite.security_id) : [...favorites, favorite].slice(-100) })
}
