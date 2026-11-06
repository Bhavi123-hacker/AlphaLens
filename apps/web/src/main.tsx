import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './App'
import { readRetry, readRetryDelay } from './lib/readPolicy'
import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'
import './styles.css'
import './terminal.css'

const client = new QueryClient({ defaultOptions: { queries: {
  staleTime: 300_000, gcTime: 600_000, refetchOnWindowFocus: false,
  networkMode: 'always',
  retry: readRetry,
  retryDelay: readRetryDelay,
} } })
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider></React.StrictMode>,
)
