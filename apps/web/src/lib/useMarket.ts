import { useQuery } from '@tanstack/react-query'
import { readMarket } from '../api/visual'
export function useMarket(session = '') { return useQuery({ queryKey: ['visual-market', session], queryFn: ({ signal }) => readMarket(session, signal), staleTime: 300_000, retry: 1 }) }
