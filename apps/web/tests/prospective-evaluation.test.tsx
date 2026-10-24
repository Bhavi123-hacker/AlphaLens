import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
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
  expect(screen.getByText('Insufficient forward evaluation data.')).toBeInTheDocument()
  expect(within(table).getByRole('columnheader', {name: 'F1'})).toBeInTheDocument()
  expect(within(table).getByRole('columnheader', {name: 'ROC-AUC'})).toBeInTheDocument()
})

function mount(data: Record<string, unknown>) {
  // All numerical examples in this test are synthetic TEST_ONLY UI contracts.
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({data,
    source:'TEST_ONLY',version:'TEST_ONLY',as_of_session:null,artifact_id:null,
    classification:{data_reality:'TEST_ONLY',usage_classification:'TEST_ONLY',final_vintage:null,research_profile:null,p1_production_data_clearance:'OPEN',production_market_data_use:'NOT_CLEARED'},
    provenance:{},evidence_status:'AVAILABLE',quality_status:'TEST_ONLY',missing_data_reasons:[],page:null}))))
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ProspectiveEvaluation/></QueryClientProvider>)
}

it('shows missing full-cohort Top-N evidence despite all five selected outcomes existing', async () => {
  const pending = { selected_securities: 5, qualified_selected_outcomes: 5, hits: null, hit_rate: null }
  mount({as_of:'2025-01-01T00:00:00Z',matured_outcomes:5,
    top_n:{declarations:1,complete_declarations:0,results:[{
      declaration_id:'TEST_ONLY_PENDING',observation_session:'2025-01-01',declared_securities:7,
      qualified_outcomes:6,complete:false,equal_cohort_hit_rate:null,
      selections:{score:{'5':pending,'10':{...pending,selected_securities:7,qualified_selected_outcomes:6},'20':{...pending,selected_securities:7,qualified_selected_outcomes:6}}}
    }]}})
  await userEvent.click(screen.getByText('Inspect point-in-time prospective evidence'))
  const table = await screen.findByRole('table', {name:'Frozen Top-N forward hit rates'})
  expect(table).toHaveTextContent('6 / 7')
  expect(table).toHaveTextContent('5 / 5 selected outcomes')
  expect(table).toHaveTextContent('Awaiting full cohort')
  expect(table).toHaveTextContent('Unavailable')
  expect(table).not.toHaveTextContent('%')
  expect(screen.getByText(/Overlapping declarations are not pooled/)).toBeInTheDocument()
})

it('renders provided matured classifier metrics, matched baselines and capped frozen selections', async () => {
  mount({as_of:'2025-01-10T00:00:00Z',matured_outcomes:7,
    metrics:{score:{samples:7,accuracy:0.5,balanced_accuracy:0.5,precision:0.5,recall:0.5,f1:0.5,roc_auc:0.625,brier_score:0.25}},
    baseline_comparisons:{baseline_momentum_score:{matched_samples:6,excluded_missing_pairs:1,candidate:{accuracy:0.5},baseline:{accuracy:0.25},candidate_minus_baseline:{balanced_accuracy:0.25}}},
    top_n:{declarations:1,complete_declarations:1,results:[{
      declaration_id:'TEST_ONLY_COMPLETE',observation_session:'2025-01-01',declared_securities:7,
      qualified_outcomes:7,complete:true,equal_cohort_hit_rate:3/7,
      selections:{score:{'5':{selected_securities:5,qualified_selected_outcomes:5,hits:2,hit_rate:0.4},'10':{selected_securities:7,qualified_selected_outcomes:7,hits:3,hit_rate:3/7},'20':{selected_securities:7,qualified_selected_outcomes:7,hits:3,hit_rate:3/7}}}
    }]}})
  await userEvent.click(screen.getByText('Inspect point-in-time prospective evidence'))
  const metrics = await screen.findByRole('table',{name:'Prospective model and baseline evaluation'})
  expect(metrics).toHaveTextContent('0.6250')
  expect(metrics).toHaveTextContent('50.00%')
  const ranking = screen.getByRole('table',{name:'Frozen Top-N forward hit rates'})
  expect(ranking).toHaveTextContent('40.00%')
  expect(ranking).toHaveTextContent('7 / 7 selected outcomes')
  expect(ranking).toHaveTextContent('Complete reference cohort')
  expect(screen.getByRole('table',{name:'Matched prospective baseline comparisons'})).toHaveTextContent('25.00%')
  expect(screen.queryByText('Insufficient forward evaluation data.')).not.toBeInTheDocument()
  expect(screen.getByText(/Brier and score bins describe uncalibrated scores/)).toBeInTheDocument()
})
