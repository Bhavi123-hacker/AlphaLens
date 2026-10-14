import { useQuery } from '@tanstack/react-query'
import { get } from './client'
import { workspaceSchema } from './personal'
export function usePersonal() { return useQuery({ queryKey: ['personal-workspace'], queryFn: ({ signal }) => get('/personal/workspace', workspaceSchema, signal), retry: false, staleTime: 15_000, gcTime: 0 }) }
