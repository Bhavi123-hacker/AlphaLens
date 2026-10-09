import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './App'
import { APIError } from './api/client'
import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'
import './styles.css'

const client = new QueryClient({ defaultOptions: { queries: {
  staleTime: 300_000, gcTime: 600_000, refetchOnWindowFocus: false,
  networkMode: 'always',
  retry: (count, error) => count < 1 && error instanceof APIError && [0, 429, 502, 504].includes(error.status),
  retryDelay: 1200,
} } })
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider></React.StrictMode>,
)
