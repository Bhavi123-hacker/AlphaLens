import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StockResearch } from '../src/components/StockResearch'
import { SequenceResearch } from '../src/components/SequenceResearch'

vi.mock('../src/components/Chart',()=>({Chart:({label}:{label:string})=><div role="img" aria-label={label}/>}))
const envelope=(data:unknown)=>new Response(JSON.stringify({data,source:'TEST_ONLY',version:'TEST_ONLY',as_of_session:null,artifact_id:null,classification:{data_reality:'TEST_ONLY',usage_classification:'TEST_ONLY',final_vintage:null,research_profile:null,p1_production_data_clearance:'OPEN',production_market_data_use:'NOT_CLEARED'},provenance:{},evidence_status:'AVAILABLE',quality_status:'TEST_ONLY',missing_data_reasons:[],page:null}))
function mount(element:React.ReactNode){render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{element}</QueryClientProvider></MemoryRouter>)}
afterEach(()=>vi.unstubAllGlobals())
it('renders immutable forecast history with pending outcomes and no invented realized return',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(envelope({state:'AVAILABLE',key:'TEST_ONLY',v2:null,lstm:null,
    historical_comparisons:[],target:'TEST_ONLY_NEXT_OPEN',prospective_outcomes:0,
    prospective_history:{forecast_count:1,unique_decisions:1,pending_forecasts:1,matured_outcomes:0,excluded_outcomes:0,
      rows:[{store:'expanded',forecast_id:'TEST_ONLY_FORECAST',forecast:{session:'2026-10-23',recorded_at:'2026-10-24T16:00:00Z',model_id:'TEST_ONLY_MODEL',score:0.61},outcome:null}]},
    accepted_rankings:0,provider_requests:0,missing_evidence:['TEST_ONLY future evidence']})))
  mount(<StockResearch instrumentKey="TEST_ONLY"/>)
  await userEvent.click(screen.getByText('Inspect experimental predictions, baselines and observed historical outcomes'))
  await screen.findByText('Recorded prospective forecasts and matured outcomes')
  await userEvent.click(screen.getByText('Recorded prospective forecasts and matured outcomes'))
  expect(await screen.findByRole('table',{name:'Saved stock forecast and outcome history'})).toBeInTheDocument()
  expect(screen.getByText('Pending qualified future evidence')).toBeInTheDocument()
  expect(screen.getByText('Realized return unavailable')).toBeInTheDocument()
  expect(screen.queryByText(/Observed price-component return 0/)).not.toBeInTheDocument()
})
it('loads only explicitly opened saved stock evidence and preserves separate score and return targets',async()=>{
  const fetch=vi.fn().mockResolvedValue(envelope({state:'AVAILABLE',key:'TEST_ONLY',v2:{score:0.61},lstm:{score:0.52},historical_comparisons:[{decision_session:'2025-01-01',target_session:'2025-01-08',actual_price_component_return:-0.02,actual_positive:0,ridge_return_estimate:0.01,scores:{LSTM:0.52}}],target:'TEST_ONLY_NEXT_OPEN',prospective_outcomes:2,prospective_history:{matured_outcomes:2,rows:[]},accepted_rankings:0,provider_requests:0,missing_evidence:['TEST_ONLY future evidence']}))
  vi.stubGlobal('fetch',fetch)
  mount(<StockResearch instrumentKey="TEST_ONLY"/>)
  expect(fetch).not.toHaveBeenCalled()
  await userEvent.click(screen.getByText('Inspect experimental predictions, baselines and observed historical outcomes'))
  expect(await screen.findByText('0.610000')).toBeInTheDocument()
  expect(screen.getByText('0.520000')).toBeInTheDocument()
  expect(screen.getByText('2',{exact:true})).toBeInTheDocument()
  expect(screen.getByText('Recorded prospective forecasts and matured outcomes')).toBeInTheDocument()
  expect(screen.getByRole('img',{name:'Known-period model versus observed outcomes; no prospective performance'})).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][0]).toBe('/api/v1/nse-market/stock-research?key=TEST_ONLY&limit=50')
  expect(screen.getByText(/Classifiers?|Classifier scores and return estimates have distinct axes/)).toBeInTheDocument()
})
it('displays actual comparison values without claiming independent acceptance',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(envelope({state:'EXPERIMENTAL_UNVALIDATED',edge_status:'NO_DEMONSTRATED_EDGE',architecture:'TEST_ONLY_LSTM',feature_version:'TEST_ONLY',comparisons:{LSTM:{metrics:{balanced_accuracy:0.49,brier_score:0.26}},mean_reversion:{metrics:{balanced_accuracy:0.51}}}})))
  mount(<SequenceResearch/>)
  expect(await screen.findByText('0.49000')).toBeInTheDocument()
  expect(screen.getByText('0.51000')).toBeInTheDocument()
  expect(screen.getByText(/No new model is independently accepted/)).toBeInTheDocument()
})
