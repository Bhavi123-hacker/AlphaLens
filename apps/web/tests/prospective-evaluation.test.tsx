import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProspectiveEvaluation } from '../src/components/ProspectiveEvaluation'

// TEST_ONLY fixture verifies zero outcomes never becomes zero-percent accuracy.
afterEach(() => vi.unstubAllGlobals())
it('loads frozen evidence only on request and leaves unmatured accuracy unavailable', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({data:{as_of:'2025-01-01T00:00:00Z',raw_forecast_records:2,unique_decisions:1,matured_outcomes:0,not_evaluated_decisions:1,metrics:{score:{samples:0,accuracy:null,balanced_accuracy:null,brier_score:null}}},source:'TEST_ONLY',version:'TEST_ONLY',as_of_session:null,artifact_id:null,classification:{data_reality:'TEST_ONLY',usage_classification:'TEST_ONLY',final_vintage:null,research_profile:null,p1_production_data_clearance:'OPEN',production_market_data_use:'NOT_CLEARED'},provenance:{},evidence_status:'AVAILABLE',quality_status:'TEST_ONLY',missing_data_reasons:[],page:null})))
  vi.stubGlobal('fetch', fetch)
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ProspectiveEvaluation/></QueryClientProvider>)
  expect(fetch).not.toHaveBeenCalled()
  await userEvent.click(screen.getByText('Inspect point-in-time prospective evidence'))
  expect(await screen.findByText('PROSPECTIVE_EVALUATION_PENDING')).toBeInTheDocument()
  expect(screen.getByText('Qualified matured decisions').parentElement).toHaveTextContent('0')
  const table=screen.getByRole('table',{name:'Prospective model and baseline evaluation'})
  expect(table).toHaveTextContent('Unavailable')
  expect(table).not.toHaveTextContent('0.00%')
  expect(String(fetch.mock.calls[0][0])).toContain('/nse-market/prospective-evaluation')
})
