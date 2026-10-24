import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UniverseCoverage } from '../src/components/UniverseCoverage'

// TEST_ONLY independent denominators; never genuine market or ML performance.
afterEach(() => vi.unstubAllGlobals())
it('separates the full saved master from dated features, predictions and update success', async () => {
  const data = { supported_equities:3188,searchable_equities:3188,available_saved_prices:500,
    latest_retained_session:'2026-10-21',latest_session_prices:248,configured_collection_securities:500,
    sufficient_ml_features_latest_session:156,feature_session:'2026-10-21',saved_compatible_predictions:302,
    prediction_observation_session:'2026-10-19',latest_session_predictions:0,dated_ranking_eligible_predictions:302,
    accepted_ml_predictions:0,top_n_returnable:{'5':5,'10':10,'20':20},exclusions:{no_saved_price:2688},
    latest_feature_exclusion_reasons:{TEST_ONLY_MISSING:1},unsupported_master_records:{TEST_ONLY_FUND:1},
    identity:{state:'STALE',observed_at:'2026-10-22T05:15:49Z'},daily_update_success_rate:null,
    daily_update_success_rate_reason:'TEST_ONLY_NOT_RUN_SUCCESS',provider_requests:0,
    limitations:['TEST_ONLY overlapping exclusions are not additive'] }
  const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({data,source:'TEST_ONLY',version:'TEST_ONLY',
    as_of_session:null,artifact_id:null,classification:{data_reality:'TEST_ONLY',usage_classification:'TEST_ONLY',
      final_vintage:null,research_profile:null,p1_production_data_clearance:'OPEN',production_market_data_use:'NOT_CLEARED'},
    provenance:{},evidence_status:'AVAILABLE',quality_status:'TEST_ONLY',missing_data_reasons:[],page:null})))
  vi.stubGlobal('fetch',fetch)
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><UniverseCoverage/></QueryClientProvider>)
  expect(await screen.findByText('3,188 / 3,188')).toBeInTheDocument()
  expect(screen.getByText(/retained coverage does not prove daily job success/)).toBeInTheDocument()
  expect(screen.getByText(/No 302-stock or 500-stock ranking cap applies/)).toBeInTheDocument()
  expect(screen.getByText('2026-10-19')).toBeInTheDocument()
  expect(screen.getByText('2026-10-21')).toBeInTheDocument()
  expect(fetch.mock.calls[0][0]).toBe('/api/v1/nse-market/universe-coverage')
})
