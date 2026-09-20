/* DOM + real local HTTP integration. Optional test dependency: jsdom.
 * Run: node scripts/live-dom-test.cjs
 * No browser automation or external accounts are used.
 */
const {JSDOM, VirtualConsole} = require('jsdom');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'errandloop-dom-'));
const base = 'http://127.0.0.1:8129';
const windows = [];
const errors = [];
const server = spawn(process.env.ERRANDLOOP_PYTHON || 'python', ['-m','app.server','--port','8129'], {
  env: {...process.env, ERRANDLOOP_LIVE_DB:path.join(temp,'groups.sqlite3')}
});
const poll = async test => {
  for(let i=0;i<200;i++){if(await test())return;await new Promise(r=>setTimeout(r,20));}
  throw new Error('Timed out waiting for UI response');
};
function client(){
  let cookie='';
  return {get cookie(){return cookie;}, async request(p,options={}){
    const result=await fetch(new URL(p,base),{...options,headers:{...options.headers,Origin:base,Cookie:cookie}});
    const next=result.headers.get('set-cookie');if(next)cookie=next.split(';')[0];
    return result;
  }};
}
async function page(client, script, fragment=""){
  const html=await (await client.request('/')).text();
  const virtualConsole=new VirtualConsole();
  virtualConsole.on('jsdomError',e=>{if(!e.message.includes('navigation'))errors.push(e.message);});
  const dom=new JSDOM(html,{url:base+fragment,runScripts:'outside-only',virtualConsole});
  windows.push(dom.window);
  dom.window.fetch=client.request.bind(client);
  dom.window.AbortSignal=AbortSignal;
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  dom.window.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  const code=fs.readFileSync('app/static/'+script,'utf8');
  await dom.window.eval('(async()=>{'+code+'\n})()');
  return dom.window;
}
function submit(window,id,fields){
  const form=window.document.querySelector(id);
  for(const [key,value] of Object.entries(fields))form.elements.namedItem(key).value=value;
  form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));
}
(async()=>{
  await new Promise((resolve,reject)=>{server.stdout.once('data',resolve);server.once('error',reject);server.once('exit',c=>reject(new Error('Server exited '+c)));});
  const alice=client(),bob=client();
  const first=await page(alice,'onboarding.js');
  submit(first,'#account-form',{name:'Alice Test',username:'alice',password:'test-password-for-alice',group_name:'Maple House',meeting:'Reception',places:'Actual shop\nActual library'});
  await poll(()=>Boolean(alice.cookie));
  let board=await (await alice.request('/api/board')).json();
  assert.equal(board.members.length,1);assert.equal(board.trips.length,0);
  const second=await page(bob,'onboarding.js','/#join='+board.group.id);
  assert.equal(second.document.querySelector('[data-mode="join"]').getAttribute('aria-pressed'),'true');
  assert.equal(second.document.querySelector('#account-form').elements.group_code.value,board.group.id);
  assert.equal(second.location.hash,'');
  submit(second,'#account-form',{name:'Bob Test',username:'bob',password:'test-password-for-bob',group_code:board.group.id});
  await poll(()=>Boolean(bob.cookie));
  const app=await page(alice,'app.js');
  assert.equal(app.document.querySelector('#actor').disabled,true);
  assert.match(app.document.body.textContent,/Alice Test/);
  assert.match(app.document.body.textContent,/Maple House/);
  assert(!app.document.body.textContent.includes('Sana'));
  assert.match(app.document.querySelector('.setup-steps').textContent,/Post your planned trip/);
  app.document.querySelector('[data-action="add-trip"]').click();
  submit(app,'#post-form',{destination:board.places[0].id,note:'Real user-created trip'});
  await poll(()=>app.document.body.textContent.includes('Real user-created trip'));
  const bobPage=await page(bob,'app.js');
  assert.match(bobPage.document.body.textContent,/Real user-created trip/);
  assert.match(bobPage.document.querySelector('#actor').textContent,/Bob Test/);
  app.document.querySelector('[data-action="group"]').click();
  assert.match(app.document.querySelector('#modal').textContent,new RegExp(board.group.id));
  assert.equal(app.document.querySelector('[aria-label="Invitation link"]').value,base+'/#join='+board.group.id);
  assert.match(app.document.querySelector('#modal').textContent,/works on this computer only/);
  submit(app,'#place-form',{name:'Actual print shop'});
  await poll(()=>app.document.querySelector('#modal').textContent.includes('Actual print shop'));
  // Exercise the actual circle controls with separate signed-in browser clients.
  async function action(who,command,data){
    const snapshot=await (await who.request('/api/board')).json();
    const response=await who.request('/api/actions/'+command,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:snapshot.version,operation:crypto.randomUUID(),...data})});
    const result=await response.json();assert.equal(response.status,200,JSON.stringify(result));return result;
  }
  const now=Math.floor(Date.now()/1000);
  await action(alice,'request',{destination:board.places[1].id,item:'Library reservation',ready:now,deadline:now+7200,units:1});
  const help=await page(alice,'app.js');
  help.document.querySelector('[data-action="match-help"]').click();
  assert.match(help.document.querySelector('#modal').textContent,/Nobody else has posted/);
  assert.match(help.document.querySelector('#modal').textContent,/Only change a time/);
  await action(bob,'trip',{destination:board.places[1].id,depart:now+1800,returns:now+3600,capacity:2});
  await action(bob,'request',{destination:board.places[0].id,item:'Prepared shop order',ready:now,deadline:now+7200,units:1});
  const review=await page(alice,'app.js');
  review.document.querySelector('[data-action="match"]').click();
  assert.match(review.document.querySelector('.match-proof').textContent,/Deadline margin/);
  assert.match(review.document.querySelector('.match-proof').textContent,/1 of 2 spaces needed/);
  review.document.querySelector('[data-action="propose"]').click();
  await poll(()=>Boolean(review.document.querySelector('[data-action="cancel-loop-prompt"]')));
  const consent=await page(bob,'app.js');
  consent.document.querySelector('[data-action="loop"]').click();
  consent.document.querySelector('[data-action="accept"]').click();
  await poll(()=>Boolean(consent.document.querySelector('[data-action="collected"]')));
  for(const who of [alice,bob]){
    const w=await page(who,'app.js');w.document.querySelector('[data-action="loop"]').click();
    const collect=w.document.querySelector('[data-action="collected"]');
    if(collect){collect.click();await poll(()=>!w.document.querySelector('[data-action="collected"]'));}
  }
  for(const who of [alice,bob]){
    const w=await page(who,'app.js');w.document.querySelector('[data-action="loop"]').click();
    assert.equal(w.document.querySelectorAll('[data-action="received"]').length,1);
    w.document.querySelector('[data-action="received"]').click();
    await poll(()=>!w.document.querySelector('[data-action="received"]'));
  }
  const final=await page(alice,'app.js');
  assert.match(final.document.querySelector('.feature').textContent,/You closed the circle/);
  assert.match(final.document.querySelector('.feature').textContent,/View completed exchange/);
  assert.match(final.document.querySelector('.progress-counts').textContent,/2receiver-confirmed handovers1completed circles/);
  final.document.querySelector('[data-action="guide"]').click();
  assert.match(final.document.querySelector('#modal').textContent,/Post both sides/);
  // A three-person exchange where there is no compatible two-person swap.
  const cara=client();const joinPage=await page(cara,'onboarding.js');
  joinPage.document.querySelector('[data-mode="join"]').click();
  submit(joinPage,'#account-form',{name:'Cara Test',username:'cara',password:'test-password-for-cara',group_code:board.group.id});
  await poll(()=>Boolean(cara.cookie));
  board=await (await alice.request('/api/board')).json();
  const places=board.places.map(p=>p.id);
  for(const [who,going,need,item] of [[alice,places[0],places[1],'Reserved book'],[bob,places[1],places[2],'Print envelope'],[cara,places[2],places[0],'Prepared order']]){
    await action(who,'trip',{destination:going,depart:now+1800,returns:now+3600,capacity:1});
    await action(who,'request',{destination:need,item,ready:now,deadline:now+7200,units:1});
  }
  board=await (await alice.request('/api/board')).json();
  assert.equal(board.matching.candidates.length,1);
  assert.equal(board.matching.candidates[0].members.length,3);
  const three=await page(alice,'app.js');three.document.querySelector('[data-action="match"]').click();
  assert.match(three.document.querySelector('.match-proof').textContent,/A pair swap cannot do this/);
  assert.equal(three.document.querySelectorAll('.proof-row').length,3);
  three.document.querySelector('[data-action="propose"]').click();
  await poll(()=>Boolean(three.document.querySelector('[data-action="cancel-loop-prompt"]')));
  for(const who of [bob,cara]){
    const w=await page(who,'app.js');w.document.querySelector('[data-action="loop"]').click();
    w.document.querySelector('[data-action="accept"]').click();
    await poll(()=>!w.document.querySelector('[data-action="accept"]'));
  }
  const start=await page(alice,'app.js');start.document.querySelector('[data-action="loop"]').click();
  assert.match(start.document.querySelector('.next-step').textContent,/Your next step: collect/);
  start.document.querySelector('[data-action="collected"]').click();
  await poll(()=>!start.document.querySelector('[data-action="collected"]'));
  // Plans change after goods are collected: preserve custody, do not rematch.
  const cancel=await page(bob,'app.js');cancel.document.querySelector('[data-action="loop"]').click();
  cancel.document.querySelector('[data-action="cancel-loop-prompt"]').click();
  cancel.document.querySelector('[data-action="cancel-loop"]').click();
  await poll(()=>cancel.document.body.textContent.includes('Let’s finish'));
  board=await (await alice.request('/api/board')).json();
  assert.equal(board.loops[0].status,'needs_handoff');
  assert.equal(board.matching.candidates.length,0);
  for(const who of [bob,cara]){
    const w=await page(who,'app.js');w.document.querySelector('[data-action="loop"]').click();
    assert.match(w.document.querySelector('#modal').textContent,/Someone reported a problem/);
    w.document.querySelector('[data-action="collected"]').click();
    await poll(()=>!w.document.querySelector('[data-action="collected"]'));
  }
  for(const who of [alice,bob,cara]){
    const w=await page(who,'app.js');w.document.querySelector('[data-action="loop"]').click();
    assert.equal(w.document.querySelectorAll('[data-action="received"]').length,1);
    w.document.querySelector('[data-action="received"]').click();
    await poll(()=>!w.document.querySelector('[data-action="received"]'));
  }
  const complete=await page(alice,'app.js');
  assert.match(complete.document.querySelector('.progress-counts').textContent,/5receiver-confirmed handovers2completed circles/);
  const failed=await page(alice,'app.js');
  failed.document.querySelector('#app').innerHTML='<div class="loading">Loading</div>';
  failed.eval(fs.readFileSync('app/static/boot.js','utf8'));
  failed.dispatchEvent(new failed.Event('error'));
  assert.equal(failed.document.querySelector('#app .loading'),null);
  assert.match(failed.document.querySelector('#app').textContent,/The board could not start/);
  assert.deepEqual(errors,[]);
  console.log('PASS: real onboarding forms, separate accounts, empty board, shared user-created post, signed-in identity, group invitation, owner-added location, match explanation, mutual consent, collection, recipient-only receipt, completed metrics, live guide, first-use checklist, three-person-only circle, cancellation after pickup, preserved handovers and recovery to completion.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{
  windows.forEach(w=>w.close());server.kill();fs.rmSync(temp,{recursive:true,force:true});
});
