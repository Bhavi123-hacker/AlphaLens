import { test, expect, type Page } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { ProviderSnapshot, ProviderInstrument } from '../../src/api/terminal'
import { currency, localTime } from '../../src/lib/format'
import { signIn } from './auth-setup'

// Real protected provider requests. No interception, price-bearing artifacts or fixtures.
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

test('primary selected-stock dashboard shows genuine accepted LTP or explicit dated EOD fallback',async({page})=>{
  test.setTimeout(180_000)
  const {items}=await observe(page)
  expect(items).toHaveLength(6)
  for(const item of items){
    await page.goto('/stocks/'+encodeURIComponent('upstox:'+item.instrument_key))
    const response=page.waitForResponse(r=>r.url().includes('/upstox-private/snapshot?'))
    await page.getByRole('button',{name:'Load Upstox observations',exact:true}).click()
    const fresh=(await(await response).json()).data.items[0] as ProviderSnapshot
    expect(fresh.instrument_key===item.instrument_key).toBe(true)
    const q=fresh.quote;const valid=q.state==='VALIDATED_SNAPSHOT'
    expect(await page.locator('.headline-price').innerText()==='₹'+currency(valid?q.ltp:fresh.latest_close)).toBe(true)
    if(valid){await expect(page.getByText('Last traded price · quote snapshot',{exact:true})).toBeVisible();await expect(page.getByText(localTime(q.last_trade_at),{exact:true})).toBeVisible()}
    else{await expect(page.getByText(/Current quote:/)).toBeVisible();await expect(page.getByText(/The daily candle price above is distinct from LTP/)).toBeVisible()}
    await expect(page.getByTestId('quote-clock-evidence')).toContainText('unauthenticated')
    await expect(page.getByRole('img',{name:`Upstox ${fresh.symbol} daily OHLCV ending ${fresh.latest_session}`})).toBeVisible()
    await expect(page.getByRole('button',{name:'SMA 20',exact:true})).toBeEnabled()
    await expect(page.getByRole('button',{name:'RSI',exact:true})).toBeEnabled()
    expect(fresh.indicators.rsi_14.points.at(-1)?.session===fresh.latest_session).toBe(true)
  }
})
