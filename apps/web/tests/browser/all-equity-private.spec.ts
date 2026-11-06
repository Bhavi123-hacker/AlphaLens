import { expect, test } from '@playwright/test'

type Identity = {instrument_key:string; symbol:string; isin:string; exchange:string; instrument_type:string; eligible_common_equity:boolean}

test('dated official NSE/BSE catalog: all identity API pages and 100 distinct saved stock browsers', async ({page,baseURL}, testInfo) => {
  test.skip(process.env.ALPHALENS_ALL_EQUITY_BROWSER !== '1','Requires authenticated private saved-data deployment')
  test.setTimeout(1_800_000)
  const forbidden:string[]=[]
  const failures:string[]=[]
  const consoleErrors:string[]=[]
  page.on('pageerror',error=>consoleErrors.push(error.message))
  page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text())})
  page.on('response',response=>{if(response.status()>=500)failures.push(`${response.status()} ${new URL(response.url()).pathname}`)})
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url())
    if(url.origin!==new URL(baseURL!).origin || url.searchParams.get('refresh')==='true' || /upstox-private/.test(url.pathname)){
      forbidden.push(url.pathname);return route.abort()
    }
    return route.continue()
  })
  const all:Identity[]=[]
  let total=1
  for(let number=1;all.length<total;number++){
    const response=await page.request.get(`/api/v1/nse-market/universe?page=${number}&page_size=100`)
    expect(response.status()).toBe(200)
    const data=(await response.json()).data as {total:number;rows:Identity[];provider_requests:number}
    await response.dispose()
    expect(data.provider_requests).toBe(0)
    total=data.total
    all.push(...data.rows)
    expect(number).toBeLessThan(1000)
  }
  expect(all.length).toBe(total)
  expect(new Set(all.map(row=>row.instrument_key)).size).toBe(total)
  expect(all.some(row=>row.exchange==='NSE')).toBe(true)
  expect(all.some(row=>row.exchange==='BSE')).toBe(true)
  for(const identity of all){
    const response=await page.request.get('/api/v1/nse-market/saved-history',{params:{key:identity.instrument_key}})
    expect(response.status(),identity.instrument_key).toBe(200)
    const data=(await response.json()).data as {provider_requests:number;security:{key:string;close:string|null;session:string|null};rows:unknown[]}
    await response.dispose()
    expect(data.provider_requests).toBe(0)
    expect(data.security.key).toBe(identity.instrument_key)
    if(data.rows.length===0){expect(data.security.close).toBeNull();expect(data.security.session).toBeNull()}
  }
  const selected=new Map<string,Identity>()
  const add=(rows:Identity[],limit:number)=>rows.slice(0,limit).forEach(row=>selected.set(row.instrument_key,row))
  add(all.filter(row=>row.exchange==='NSE'),35)
  add(all.filter(row=>row.exchange==='BSE'),35)
  const byIsin=new Map<string,Identity[]>()
  all.forEach(row=>byIsin.set(row.isin,[...(byIsin.get(row.isin)??[]),row]))
  add([...byIsin.values()].filter(rows=>rows.length>1).slice(0,10).flat(),20)
  add(all.filter(row=>row.exchange==='NSE'&&row.instrument_type!=='EQ'),10)
  const unsupported=await page.request.get('/api/v1/nse-market/universe?include_unsupported=true&q=INF&page_size=10')
  expect(unsupported.status()).toBe(200)
  add((await unsupported.json()).data.rows as Identity[],10)
  await unsupported.dispose()
  for(const row of all){if(selected.size>=110)break;selected.set(row.instrument_key,row)}
  expect(selected.size).toBeGreaterThanOrEqual(100)
  const opened=[]
  for(const identity of selected.values()){
    await page.goto('/stocks/'+encodeURIComponent('upstox:'+identity.instrument_key))
    await expect(page.getByRole('heading',{name:'Saved private OHLCV chart',exact:true})).toBeVisible()
    await expect(page.getByText('Exact saved identity: '+identity.instrument_key,{exact:false})).toBeVisible()
    await expect(page.getByText(identity.symbol,{exact:false}).first()).toBeVisible()
    if(identity.exchange==='BSE')await expect(page.getByText(/MODEL_NOT_VALIDATED_FOR_THIS_SEGMENT/)).toBeVisible()
    opened.push({key:identity.instrument_key,exchange:identity.exchange,series:identity.instrument_type})
  }
  expect(forbidden).toEqual([])
  expect(failures).toEqual([])
  expect(consoleErrors).toEqual([])
  await testInfo.attach('private-equity-browser-coverage',{body:JSON.stringify({catalog_total:total,detail_api_successes:all.length,distinct_browser_identities:opened.length,opened,provider_requests:0,console_errors:consoleErrors,server_failures:failures},null,2),contentType:'application/json'})
})

test('NSE/BSE saved discovery and detail remain responsive at five widths', async ({page,baseURL},testInfo)=>{
  test.skip(process.env.ALPHALENS_ALL_EQUITY_BROWSER !== '1','Requires authenticated private saved-data deployment')
  test.setTimeout(360_000)
  const forbidden:string[]=[],failures:string[]=[],consoleErrors:string[]=[]
  page.on('pageerror',error=>consoleErrors.push(error.message))
  page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text())})
  page.on('response',response=>{if(response.status()>=500)failures.push(`${response.status()} ${new URL(response.url()).pathname}`)})
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url())
    if(url.origin!==new URL(baseURL!).origin || url.searchParams.get('refresh')==='true' || /upstox-private/.test(url.pathname)){
      forbidden.push(url.pathname);return route.abort()
    }
    return route.continue()
  })
  for(const width of [1600,1366,768,390,320]){
    await page.setViewportSize({width,height:1000})
    await page.goto('/nse-market')
    await expect(page.getByRole('heading',{name:'All supported ordinary NSE / BSE equities'})).toBeVisible()
    await page.getByLabel('Equity exchange').selectOption('BSE')
    await page.getByLabel('Search current NSE / BSE common equities').fill('RELIANCE')
    const table=page.getByRole('table',{name:'Verified dated NSE / BSE universe'})
    await expect(table.getByRole('link',{name:'RELIANCE',exact:true})).toBeVisible()
    const geometry=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll<HTMLElement>('body *')].filter(element=>!element.closest('.table-scroll')).map(element=>({tag:element.tagName,classes:element.className,parent:element.parentElement?.className,text:element.textContent?.slice(0,120),right:element.getBoundingClientRect().right,width:element.getBoundingClientRect().width})).filter(element=>element.right>innerWidth+1&&element.width>0)}))
    expect(geometry.scrollWidth<=geometry.width+1,JSON.stringify(geometry)).toBe(true)
    await table.getByRole('link',{name:'RELIANCE',exact:true}).click()
    await expect(page.getByRole('heading',{name:'Saved private OHLCV chart',exact:true})).toBeVisible()
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
  }
  expect(forbidden).toEqual([])
  expect(failures).toEqual([])
  expect(consoleErrors).toEqual([])
  await testInfo.attach('private-equity-responsive-coverage',{body:JSON.stringify({viewport_widths:[1600,1366,768,390,320],provider_requests:0,console_errors:consoleErrors,server_failures:failures},null,2),contentType:'application/json'})
})
