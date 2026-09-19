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
async function page(client, script){
  const html=await (await client.request('/')).text();
  const virtualConsole=new VirtualConsole();
  virtualConsole.on('jsdomError',e=>{if(!e.message.includes('navigation'))errors.push(e.message);});
  const dom=new JSDOM(html,{url:base,runScripts:'outside-only',virtualConsole});
  windows.push(dom.window);
  dom.window.fetch=client.request.bind(client);
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
  const second=await page(bob,'onboarding.js');
  second.document.querySelector('[data-mode="join"]').click();
  submit(second,'#account-form',{name:'Bob Test',username:'bob',password:'test-password-for-bob',group_code:board.group.id});
  await poll(()=>Boolean(bob.cookie));
  const app=await page(alice,'app.js');
  assert.equal(app.document.querySelector('#actor').disabled,true);
  assert.match(app.document.body.textContent,/Alice Test/);
  assert.match(app.document.body.textContent,/Maple House/);
  assert(!app.document.body.textContent.includes('Sana'));
  app.document.querySelector('[data-action="add-trip"]').click();
  submit(app,'#post-form',{destination:board.places[0].id,note:'Real user-created trip'});
  await poll(()=>app.document.body.textContent.includes('Real user-created trip'));
  const bobPage=await page(bob,'app.js');
  assert.match(bobPage.document.body.textContent,/Real user-created trip/);
  assert.match(bobPage.document.querySelector('#actor').textContent,/Bob Test/);
  app.document.querySelector('[data-action="group"]').click();
  assert.match(app.document.querySelector('#modal').textContent,new RegExp(board.group.id));
  submit(app,'#place-form',{name:'Actual print shop'});
  await poll(()=>app.document.querySelector('#modal').textContent.includes('Actual print shop'));
  assert.deepEqual(errors,[]);
  console.log('PASS: real onboarding forms, separate accounts, empty board, shared user-created post, signed-in identity, group invitation, owner-added location.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{
  windows.forEach(w=>w.close());server.kill();fs.rmSync(temp,{recursive:true,force:true});
});
