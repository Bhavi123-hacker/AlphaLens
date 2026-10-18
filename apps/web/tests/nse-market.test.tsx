import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { NseMarket } from '../src/pages/NseMarket'
import { marketResearchSchema, universePageSchema } from '../src/api/nse-market'

// TEST_ONLY contracts verify rendering; these fixtures are not real NSE evidence.
function fixture() {
  return {state:'AVAILABLE', counts:{verified_eligible_common_equities:3,validated_historical_stocks:2,experimental_ml_eligible_stocks:1,independently_accepted_ml_stocks:0}, coverage:{start:'2025-01-01',end:'2025-12-01'},scores:{model_id:'TEST_ONLY_MODEL',generated_at:'2025-12-02T01:00:00Z',observation_session:'2025-12-01'}, candidates:[{key:'NSE_EQ|INE000000000',symbol:'TEST_ONLY_STOCK',score:0.6123456,session:'2025-12-01',observed_price:'123.45',model_id:'TEST_ONLY_MODEL',inference_at:'2025-12-02T01:00:00Z',source:'TEST_ONLY',applicability:'OUT_OF_TRAINING_COHORT_EXTRAPOLATION_UNVALIDATED',identity:{name:'TEST_ONLY company'},risk:{},features:[0.05],feature_names:['price_return_5'],missing_evidence:['TEST_ONLY missing evidence']}],total:1,unfiltered_total:1,page:1,page_size:5,provider_requests:0,accepted_current_rankings:0,automatic_acquisition_enabled:false}
}
const master={snapshot_id:'TEST_ONLY',observed_at:'2025-12-02T01:00:00Z',total:1,page:1,page_size:25,provider_requests:0,summary:{},rows:[{instrument_key:'NSE_EQ|INE000000001',symbol:'TEST_ONLY_BE',name:'TEST_ONLY ordinary',isin:'INE000000001',series:'BE',eligible_common_equity:true}]}
function mount() {
  const fetch=vi.fn().mockImplementation((path:string)=> {
    const data=path.includes('/universe?') ? master : {...fixture(),page_size:path.includes('page_size=20') ? 20 : 5,candidates:path.includes('matches_only=true') ? [] : fixture().candidates,total:path.includes('matches_only=true') ? 0 : 1}
    return Promise.resolve(new Response(JSON.stringify({data,source:'TEST_ONLY',version:'TEST_ONLY',as_of_session:null,artifact_id:null,classification:{data_reality:'TEST_ONLY',usage_classification:'TEST_ONLY',final_vintage:null,research_profile:null,p1_production_data_clearance:'OPEN',production_market_data_use:'NOT_CLEARED'},provenance:{},evidence_status:'AVAILABLE',quality_status:'TEST_ONLY',missing_data_reasons:[],page:null})))
  })
  vi.stubGlobal('fetch',fetch)
  render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><NseMarket/></QueryClientProvider></MemoryRouter>)
  return fetch
}
afterEach(()=>vi.unstubAllGlobals())
it('separates current identity discovery from observed and experimental coverage',async()=>{
  const fetch=mount()
  expect(await screen.findByText('TEST_ONLY_STOCK')).toBeInTheDocument()
  expect(await screen.findByText('TEST_ONLY_BE')).toBeInTheDocument()
  expect(screen.getByTestId('expanded-model-score')).toHaveTextContent('0.612346')
  expect(screen.getByRole('link',{name:'TEST_ONLY_BE'})).toHaveAttribute('href','/stocks/'+encodeURIComponent('upstox:NSE_EQ|INE000000001'))
  expect(screen.getByText(/NO_DEMONSTRATED_EDGE/)).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Expanded research list size'),'20')
  await waitFor(()=>expect(fetch.mock.calls.some(([path])=>String(path).includes('page_size=20'))).toBe(true))
  expect(screen.getAllByTestId('expanded-model-score')).toHaveLength(1)
  await userEvent.click(screen.getByLabelText('Only matches to supported preferences'))
  expect(await screen.findByText('No eligible saved scores in this view')).toBeInTheDocument()
  expect(fetch.mock.calls.every(([path])=>String(path).startsWith('/api/v1/nse-market/'))).toBe(true)
})
it('rejects promoted, fabricated or unbounded workspace contracts',()=>{
  expect(marketResearchSchema.safeParse(fixture()).success).toBe(true)
  expect(marketResearchSchema.safeParse({...fixture(),accepted_current_rankings:1}).success).toBe(false)
  expect(marketResearchSchema.safeParse({...fixture(),automatic_acquisition_enabled:true}).success).toBe(false)
  expect(marketResearchSchema.safeParse({...fixture(),page_size:101}).success).toBe(false)
  expect(marketResearchSchema.safeParse({...fixture(),candidates:[{...fixture().candidates[0],score:NaN}]}).success).toBe(false)
  expect(universePageSchema.safeParse({...master,rows:[{...master.rows[0],eligible_common_equity:false}]}).success).toBe(false)
})
