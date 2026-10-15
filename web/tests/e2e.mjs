// Isolated fixture E2E. Set E2E_WEB_URL/E2E_API_URL to the test namespace.
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_ROOT ? path.join(process.env.PLAYWRIGHT_MODULE_ROOT,'playwright') : 'playwright');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const web=process.env.E2E_WEB_URL||'http://127.0.0.1:3107';
const api=process.env.E2E_API_URL||'http://127.0.0.1:8107';
// Mặc định Microsoft Edge (SRS LIM-16: Chrome hoặc Edge có ghi phiên bản). Đổi bằng E2E_BROWSER=chrome|chromium.
const channel=process.env.E2E_BROWSER||'msedge';
const out=path.resolve(process.env.E2E_OUTPUT||path.join(root,'reports/e2e'));
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,...(channel?{channel}:{})});
const report={browser:channel,version:browser.version(),runs:[]};
let failed=false;
for (const viewport of [{width:1440,height:900},{width:390,height:844}]) {
  const context=await browser.newContext({viewport});
  const page=await context.newPage();page.setDefaultTimeout(15000);
  const request=context.request;const created=[];const run={viewport,checks:[]};report.runs.push(run);
  const key=()=>crypto.randomUUID();const suffix=key().slice(0,8);
  const record=(name)=>{run.checks.push({name,passed:true});console.log(`${report.browser} ${viewport.width}: ${name}`);};
  async function upload(name,text) {
    const pending=page.waitForResponse(r=>r.url().endsWith('/api/proxy?target=upload')&&r.request().method()==='POST');
    await page.getByLabel('Chọn tài liệu .txt, .md hoặc .pdf').setInputFiles({name,mimeType:'text/plain',buffer:Buffer.from(text)});
    const response=await pending;const data=await response.json();const id=data.id||data.document_id;
    if(id&&!data.deduplicated)created.push(id);
    await page.getByLabel('Chọn tài liệu .txt, .md hoặc .pdf').waitFor({state:'visible'});
    await page.waitForFunction(()=>!document.querySelector('input[type=file]')?.disabled);
    return {id,data,status:response.status()};
  }
  try {
    assert.equal((await (await request.get(api+'/system/profile')).json()).mode,'fixture','Browser tests must stay offline');
    await page.goto(web);await page.getByRole('heading',{name:'Hỏi đáp (RAG)'}).waitFor();
    const a=await upload(`alpha-${suffix}.md`,`# Release BLUE-17\nAlpha ${suffix} must retain source citations.`);
    const b=await upload(`beta-${suffix}.txt`,`Beta ${suffix} describes another topic.`);
    assert.equal(a.status,201);assert.equal(b.status,201);
    const pickA=page.getByRole('checkbox',{name:`alpha-${suffix}.md`});const pickB=page.getByRole('checkbox',{name:`beta-${suffix}.txt`});
    await pickA.check();await page.getByRole('button',{name:'Làm mới trạng thái'}).click();
    assert.equal(await pickA.isChecked(),true);assert.equal(await pickB.isChecked(),false);
    await upload(`gamma-${suffix}.txt`,`Gamma ${suffix} newly added source.`);
    assert.equal(await pickA.isChecked(),true);assert.equal(await pickB.isChecked(),false);assert.equal(await page.getByRole('checkbox',{name:`gamma-${suffix}.txt`}).isChecked(),false);
    record('source selection survives refresh/upload without expansion');
    const row=page.locator('.doc-item').filter({hasText:`alpha-${suffix}.md`});
    await row.getByRole('button',{name:'Xem nguồn'}).focus();await page.keyboard.press('Enter');
    await page.getByRole('region',{name:'Nội dung nguồn'}).getByText(`Alpha ${suffix}`,{exact:false}).waitFor();
    await page.keyboard.press('Escape');await page.getByRole('region',{name:'Nội dung nguồn'}).waitFor({state:'detached'});
    record('keyboard source navigation and Escape close');
    await page.getByLabel('Câu hỏi về tài liệu').fill('What does Alpha require?');
    await page.getByRole('button',{name:'Hỏi',exact:true}).click();await page.locator('.answer').waitFor();
    assert.match(await page.locator('.answer').innerText(),/FIXTURE/);
    await page.locator('.citation-list button').first().click();await page.getByRole('region',{name:'Nội dung nguồn'}).locator('pre').waitFor();
    page.once('dialog',dialog=>dialog.accept());await row.getByRole('button',{name:'Xóa',exact:true}).click();
    await row.waitFor({state:'detached'});await page.getByRole('region',{name:'Nội dung nguồn'}).waitFor({state:'detached'});
    // ChatPanel refreshes citations asynchronously after the document list/source view.
    // Wait for the same required state, rather than asserting during that refresh.
    await page.waitForFunction(()=>document.querySelector('.citation-list button')?.disabled===true);
    assert.equal(await page.locator('.citation-list button').first().isDisabled(),true);
    assert.match(await page.locator('.citation-list').innerText(),/không còn khả dụng/);
    record('deletion invalidates open source and historical citation');
    const bad=await upload(`empty-${suffix}.txt`,' '.repeat(20+Math.floor(Math.random()*100)));
    assert.equal(bad.status,422);
    // Đăng ký filechooser TRƯỚC khi focus: Playwright bật chặn file chooser bất đồng bộ khi có listener.
    // keyboard.press không có bước chờ nên có thể tới trình duyệt trước, chooser mở native và event bị mất (flaky).
    const chooserPromise=page.waitForEvent('filechooser');chooserPromise.catch(()=>{});// tránh unhandled rejection nếu fail trước khi await
    const retry=page.getByLabel(`Thử lại empty-${suffix}.txt`);await retry.focus();
    assert.equal(await retry.evaluate(el=>el===document.activeElement&&!el.disabled),true);
    await page.keyboard.press('Enter');const chooser=await chooserPromise;
    const attemptPromise=page.waitForResponse(r=>r.url().endsWith(`/api/documents/${bad.id}/retry`));
    // Reuse the same bytes; invalid content remains failed and adds an attempt.
    const bytes=(await request.get(api+`/documents/${bad.id}`)).ok();assert.ok(bytes);
    await chooser.setFiles({name:`empty-${suffix}.txt`,mimeType:'text/plain',buffer:Buffer.from('changed')});
    assert.equal((await attemptPromise).status(),409);
    await page.getByRole('alert').filter({hasText:'nội dung'}).waitFor();
    record('retry input is keyboard accessible; wrong file rejected');
    // Drop a completed response; pretend reconciliation is processing for >5 polls.
    await pickB.check();let polls=0;let mutations=0;
    await page.route('**/api/operations/chat/**',async route=>{polls++;if(polls<=6)await route.fulfill({json:{status:'processing'}});else await route.continue();});
    await page.route('**/api/proxy?target=chat',async route=>{mutations++;await route.fetch();await route.abort('failed');});
    await page.getByLabel('Câu hỏi về tài liệu').fill('Tell me about Beta.');await page.getByRole('button',{name:'Hỏi',exact:true}).click();
    await page.locator('.answer').waitFor({timeout:20000});assert.ok(polls>=7);assert.equal(mutations,1);
    await page.unroute('**/api/proxy?target=chat');await page.unroute('**/api/operations/chat/**');
    record('lost response reconciles beyond five seconds without resubmission');
    let notify;const posted=new Promise(resolve=>{notify=resolve;});let release;const held=new Promise(resolve=>{release=resolve;});mutations=0;
    await page.route('**/api/proxy?target=chat',async route=>{mutations++;await route.fetch();notify();await held;try{await route.abort();}catch{}});
    await page.getByLabel('Câu hỏi về tài liệu').fill('Beta after reload?');await page.getByRole('button',{name:'Hỏi',exact:true}).click();await posted;
    const saved=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('insighthub.anon.pending.v1')));assert.equal(saved.filter(v=>v.type==='chat').length,1);
    await page.reload();release();await page.locator('.answer').waitFor();assert.equal(mutations,1);
    assert.equal(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('insighthub.anon.pending.v1')).length),0);
    record('reload restores pending chat with the original key');
    await page.unroute('**/api/proxy?target=chat');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:path.join(out,`${report.browser}-${viewport.width}.png`),fullPage:true});
    record('responsive viewport has no horizontal overflow');
  } catch(error) {
    failed=true;run.error=String(error);console.error(run.error);
    await page.screenshot({path:path.join(out,`${report.browser}-${viewport.width}-failure.png`),fullPage:true}).catch(()=>{});
  } finally {
    for(const id of new Set(created))await request.delete(api+`/documents/${id}`,{headers:{'Idempotency-Key':key()}}).catch(()=>{});
    await context.close();
  }
}
await browser.close();await fs.writeFile(path.join(out,`${report.browser}.json`),JSON.stringify(report,null,2)+'\n');
if(failed)process.exitCode=1;
