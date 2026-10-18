import { test, expect, type Page } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { ProviderSnapshot, ProviderInstrument } from '../../src/api/terminal'
import { currency, localTime } from '../../src/lib/format'
import { signIn } from './auth-setup'

// Real protected provider requests. No interception, price-bearing artifacts or fixtures.
process.env.PLAYWRIGHT_NO_COPY_PROMPT = '1'
test.use({trace:'off',screenshot:'off',video:'off'})
test.beforeEach(async({page})=>{await page.context().clearCookies();await page.goto('/login');await signIn(page)})
const symbols=['RELIANCE','BAJFINANCE','TCS','INFY','HDFCBANK','ICICIBANK']
async function observe(page:Page){
  const items:ProviderSnapshot[]=[]
  const identities:ProviderInstrument[]=[];let count=0;let calls=0
  for(const symbol of symbols){
    const response=await page.request.get('/api/v1/providers/upstox-private/instruments?q='+symbol)
    expect(response.status()).toBe(200);const master=(await response.json()).data;count=master.candidate_count
    const matches=master.instruments.filter((i:ProviderInstrument)=>i.symbol===symbol)
    expect(matches).toHaveLength(1);expect(matches[0].provider_key==='NSE_EQ|'+matches[0].isin).toBe(true);identities.push(matches[0])
  }
  for(let n=0;n<6;n+=3){
    const response=await page.request.get('/api/v1/providers/upstox-private/snapshot?instrument_keys='+encodeURIComponent(identities.slice(n,n+3).map(i=>i.provider_key).join(',')))
    expect(response.status()).toBe(200);const data=(await response.json()).data
    expect(data.retained).toBe(false);expect(data.full_nse_coverage).toBe(false);calls+=data.api_calls_this_request;items.push(...data.items)
  }
  return {items,count,calls}
}

test('six genuine current quotes must pass the bounded conservative receipt policy',async({page})=>{
  test.setTimeout(240_000)
  const {items,count,calls}=await observe(page)
  const receipts=items.map(item=>{
    const q=item.quote as ProviderSnapshot['quote']&{reported_last_trade_at?:string}
    const valid=q.state==='VALIDATED_SNAPSHOT'
    if(valid){
      const calibration=q.clock.calibration
      expect(calibration?.state).toBe('BOUNDED_INDEPENDENT_NTP_ASSUMPTION')
      expect(calibration?.evidence_age_seconds).toBeLessThanOrEqual(30)
      expect(Date.parse(q.last_trade_at!)<=Date.parse(q.snapshot_at!)&&Date.parse(q.snapshot_at!)<=Date.parse(calibration!.receipt_lower_at!)).toBe(true)
      expect(Date.parse(calibration!.receipt_upper_at!)-Date.parse(q.snapshot_at!)).toBeLessThanOrEqual(30_000)
      if(q.previous_close!=null){expect(Math.abs(Number(q.change)-(Number(q.ltp)-Number(q.previous_close)))<1e-8).toBe(true);expect(Math.abs(Number(q.change_percent)-100*(Number(q.ltp)-Number(q.previous_close))/Number(q.previous_close))<1e-8).toBe(true)}
    }else expect(q.ltp===undefined).toBe(true)
    expect(item.rows.at(-1)?.session===item.latest_session).toBe(true)
    return {symbol:item.symbol,instrument_key:item.instrument_key,quote_state:q.state,quote_generated_at:q.snapshot_at??q.reported_snapshot_at,last_trade_at:q.last_trade_at??q.reported_last_trade_at,clock:q.clock,latest_eod_session:item.latest_session,candle_count:item.rows.length,current_session_status:item.current_session_status,change_correct:valid&&q.previous_close!=null,provider_price_values_retained:false}
  })
  const accepted=receipts.filter(r=>r.quote_state==='VALIDATED_SNAPSHOT').length
  writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR!,'p34-provider-metadata.json'),JSON.stringify({verified_current_identities:count,queried_count:6,accepted_quote_count:accepted,current_quotes:accepted===6?'PASSED':'FAILED',provider_gets:calls,items:receipts},null,2))
  expect(accepted,'CURRENT_QUOTES requires six genuinely accepted quotes; EOD fallback is separate').toBe(6)
})

test('primary dashboard shows six genuine verified or explicitly indicative provider quotes',async({page})=>{
  test.setTimeout(180_000)
  const {items}=await observe(page)
  expect(items).toHaveLength(6)
  for(const item of items){
    await page.goto('/stocks/'+encodeURIComponent('upstox:'+item.instrument_key))
    const response=page.waitForResponse(r=>r.url().includes('/upstox-private/snapshot?'))
    await page.getByRole('button',{name:'Load Upstox observations',exact:true}).click()
    const fresh=(await(await response).json()).data.items[0] as ProviderSnapshot
    expect(fresh.instrument_key===item.instrument_key).toBe(true)
    const q=fresh.quote;const valid=q.state==='VALIDATED_SNAPSHOT';const indicative=fresh.indicative_quote
    // Preserve only chronology/classification when a real source or clock rejects
    // a quote. Never retain provider prices or a page DOM to diagnose failure.
    if(process.env.ALPHALENS_BROWSER_OUTPUT_DIR) writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR,'p34-display-classification-'+fresh.symbol+'.json'),JSON.stringify({instrument_key:fresh.instrument_key,symbol:fresh.symbol,quote_state:q.state,indicative_state:indicative?.state??null,delayed_display_mode:fresh.delayed_provider_display?.mode??null,reported_snapshot_at:q.snapshot_at??q.reported_snapshot_at??null,last_trade_at:q.last_trade_at??indicative?.last_trade_at??null,clock:q.clock,latest_eod_session:fresh.latest_session,price_values_retained:false},null,2))
    expect(fresh.delayed_provider_display?.mode).toBe('DELAYED_AUTHENTICATED_PROVIDER_PRICE')
    expect(fresh.delayed_provider_display!.elapsed_since_network_receipt_seconds).toBeGreaterThanOrEqual(1)
    expect(fresh.delayed_provider_display!.local_network_received_at).toBe((valid?q:indicative)!.clock.local_received_at)
    expect(fresh.delayed_provider_display!.delay_proves_chronology).toBe(false)
    await expect(page.getByTestId('delayed-provider-display')).toContainText('intentional one-second display delay')
    expect(valid||indicative?.state==='INDICATIVE_PROVIDER_QUOTE_TIME_UNCERTAIN','Private display requires a genuine classified quote').toBe(true)
    expect(await page.locator('.headline-price').innerText()==='₹'+currency(valid?q.ltp:indicative?.ltp)).toBe(true)
    if(valid){await expect(page.getByText('Last traded price · quote snapshot',{exact:true})).toBeVisible();await expect(page.getByText(localTime(q.last_trade_at),{exact:true})).toBeVisible()}
    else{
      expect(q.ltp).toBeUndefined();expect(q.state).toBe('QUOTE_TIME_REJECTED')
      expect(indicative?.strict_verified).toBe(false);expect(indicative?.financial_input_eligible).toBe(false)
      const calibration=indicative!.clock.calibration;const generation=Date.parse(indicative!.snapshot_at)
      expect(generation>Date.parse(calibration.receipt_lower_at!)&&generation<=Date.parse(calibration.receipt_upper_at!)).toBe(true)
      await expect(page.getByText('Provider quote — timing not independently verified',{exact:true})).toBeVisible()
      await expect(page.getByTestId('indicative-quote-notice')).toContainText(indicative!.raw_provider_timestamp)
      await expect(page.getByTestId('indicative-quote-notice')).toContainText(indicative!.last_trade_at)
      await expect(page.getByTestId('indicative-quote-notice')).toContainText('Not an official final close')
    }
    await expect(page.getByTestId('quote-clock-evidence')).toContainText('unauthenticated')
    await expect(page.getByRole('img',{name:`Upstox ${fresh.symbol} daily OHLCV ending ${fresh.latest_session}`})).toBeVisible()
    await expect(page.getByRole('button',{name:'SMA 20',exact:true})).toBeEnabled()
    await expect(page.getByRole('button',{name:'RSI',exact:true})).toBeEnabled()
    expect(fresh.indicators.rsi_14.points.at(-1)?.session===fresh.latest_session).toBe(true)
  }
})

test('passive quote expiry restores dated EOD fallback and retains the chart without polling',async({page})=>{
  test.setTimeout(90_000)
  await page.goto('/stocks/'+encodeURIComponent('upstox:NSE_EQ|INE002A01018'))
  let snapshotReads=0;page.on('request',r=>{if(r.url().includes('/upstox-private/snapshot?'))snapshotReads++})
  const response=page.waitForResponse(r=>r.url().includes('/upstox-private/snapshot?'))
  await page.getByRole('button',{name:'Load Upstox observations',exact:true}).click()
  const item=(await(await response).json()).data.items[0] as ProviderSnapshot
  const hasQuote=item.quote.state==='VALIDATED_SNAPSHOT'||item.indicative_quote!=null
  expect(hasQuote,'Expiry case requires a genuine initially displayable quote').toBe(true)
  await expect(page.getByText('Latest provider EOD candle close',{exact:true})).toBeVisible({timeout:40_000})
  expect(await page.locator('.headline-price').innerText()==='₹'+currency(item.latest_close)).toBe(true)
  await expect(page.getByRole('img',{name:`Upstox ${item.symbol} daily OHLCV ending ${item.latest_session}`})).toBeVisible()
  expect(snapshotReads).toBe(1)
})

test('qualified private daily collection and experimental input gaps are visible independently of accepted ML',async({page})=>{
  const response=await page.request.get('/api/v1/providers/private-eod-status')
  expect(response.status()).toBe(200)
  const status=(await response.json()).data
  expect(status.configured).toBe(true)
  expect(status.selected_count).toBe(1)
  expect(status.observations).toBe(2)
  expect(status.latest_session).toBe('2026-10-15')
  expect(status.scheduler_enabled).toBe(true)
  expect(status.prices_in_status_response).toBe(false)
  expect(status.full_nse_coverage).toBe(false)
  expect(status.inference).toBe('UNAVAILABLE')
  await page.goto('/data-health')
  await expect(page.getByRole('heading',{name:'Private selected-watchlist EOD collection',exact:true})).toBeVisible()
  await expect(page.getByText('Daily task activated',{exact:true})).toBeVisible()
  await expect(page.getByText('Accepted ML pipeline inactive',{exact:true})).toBeVisible()
  const readiness=(await(await page.request.get('/api/v1/personal/model-readiness')).json()).data
  expect(readiness.feature_support).toHaveLength(38)
  expect(readiness.current_eligible_feature_count).toBe(0)
  expect(readiness.experimental_research.classification).toBe('EXPERIMENTAL_UNVALIDATED_RESEARCH')
  expect(readiness.experimental_research.predictions_generated).toBe(0)
  expect((await page.request.get('/api/v1/daily/predictions')).status()).toBe(503)
})
