import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { get } from '../api/client'
import { jsonObject } from '../api/contracts'
import { readable } from '../lib/format'
import { Panel, QueryState, Stat } from './ui'

const count = z.number().int().nonnegative()
const schema = z.object({
  supported_equities: count, searchable_equities: count, available_saved_prices: count,
  latest_retained_session: z.string(), latest_session_prices: count,
  configured_collection_securities: count, sufficient_ml_features_latest_session: count.nullable(),
  feature_session: z.string().nullable(), saved_compatible_predictions: count,
  prediction_observation_session: z.string().nullable(), latest_session_predictions: count,
  dated_ranking_eligible_predictions: count, accepted_ml_predictions: z.literal(0),
  top_n_returnable: z.record(z.string(), count), exclusions: jsonObject,
  latest_feature_exclusion_reasons: jsonObject, unsupported_master_records: jsonObject,
  identity: z.object({ state: z.string(), observed_at: z.string() }),
  daily_update_success_rate: z.number().nullable(), daily_update_success_rate_reason: z.string(),
  provider_requests: z.literal(0), limitations: z.array(z.string()),
})

export function UniverseCoverage() {
  const query = useQuery({ queryKey: ['nse-universe-coverage'], retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => get('/nse-market/universe-coverage', schema, signal) })
  const data = query.data?.data
  return <Panel title="Measured NSE universe coverage" subtitle="Identity discovery, retained prices and model eligibility have independent dates and denominators">
    <QueryState query={query}>{data && <>
      <div className="stat-grid">
        <Stat label="Supported / searchable equities" value={`${data.supported_equities.toLocaleString()} / ${data.searchable_equities.toLocaleString()}`} />
        <Stat label="Equities with saved prices" value={data.available_saved_prices.toLocaleString()} />
        <Stat label="Latest-session sufficient ML features" value={data.sufficient_ml_features_latest_session?.toLocaleString() ?? 'Not measured'} note={data.feature_session ?? 'No feature session'} />
        <Stat label="Preserved compatible predictions" value={data.saved_compatible_predictions.toLocaleString()} note={data.prediction_observation_session ?? 'No prediction session'} />
        <Stat label="Latest-session predictions" value={data.latest_session_predictions.toLocaleString()} />
        <Stat label="Dated ranking eligible / accepted" value={`${data.dated_ranking_eligible_predictions} / ${data.accepted_ml_predictions}`} />
      </div>
      <p>Master observed {data.identity.observed_at} ({data.identity.state.toLowerCase()}). Latest retained session {data.latest_retained_session}: {data.latest_session_prices} / {data.configured_collection_securities} configured securities. Expanded live collection is not activated.</p>
      <p>Top 5 / 10 / 20 can return {data.top_n_returnable['5']} / {data.top_n_returnable['10']} / {data.top_n_returnable['20']} dated candidates from all eligible saved predictions. No 302-stock or 500-stock ranking cap applies.</p>
      <p>Daily update success rate: {data.daily_update_success_rate === null ? 'Unavailable; retained coverage does not prove daily job success.' : `${(data.daily_update_success_rate * 100).toFixed(1)}%`}</p>
      <details><summary>Per-universe exclusions and evidence limitations</summary>
        {[['Saved data / prediction exclusions', data.exclusions], ['Latest feature exclusions', data.latest_feature_exclusion_reasons], ['Unsupported master instruments', data.unsupported_master_records]].map(([title, counts]) => <div key={String(title)}><h3>{String(title)}</h3>{Object.entries(counts).map(([reason, value]) => <p key={reason}>{readable(reason)}: {String(value)}</p>)}</div>)}
        {data.limitations.map(reason => <p key={reason}>{reason}</p>)}
      </details>
    </>}</QueryState>
  </Panel>
}
