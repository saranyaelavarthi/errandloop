const live = document.body.dataset.mode === 'live';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  pin:'<path d="M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',
  bag:'<path d="M5 7h14l1 14H4L5 7Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
  book:'<path d="M4 3h13a2 2 0 0 1 2 2v16H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Zm0 14h15M7 3v14"/>',
  print:'<path d="M7 7V3h10v4M7 17H4V8h16v9h-3M7 14h10v7H7ZM16 11h1"/>',
  cup:'<path d="M4 7h12v8a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V7Zm12 1h2a3 3 0 0 1 0 6h-2M7 3v1m5-1v1"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  loop:'<path d="M19 8a8 8 0 0 0-13-3L3 8m0-5v5h5M5 16a8 8 0 0 0 13 3l3-3m0 5v-5h-5"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
};
const icon = (name, size=18) => `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.pin}</svg>`;
let state, actor = localStorage.getItem('errandloop-actor') || 'you', currentView='board', boardTab='trips', destination='all';
let dialogState=null, saving=false, toastTimer, lastFocus, connected=true;
const modal=$('#modal');
const member = id => state.members.find(m=>m.id===id) || {name:'ErrandLoop',initials:'↗',color:'green'};
const name = id => id===actor ? 'You' : member(id).name;
const place = id => state.places.find(p=>p.id===id);
const time = t => new Date(t*1000).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
const relative = t => {const minutes=Math.max(0,Math.ceil((t-Date.now()/1000)/60)); return minutes<60?`${minutes} min`:`${Math.floor(minutes/60)}h ${minutes%60}m`;};
const avatar = id => `<span class="avatar ${esc(member(id).color)}">${esc(member(id).name.replace(/\([^)]*\)/g,'').trim().split(/\s+/).map(part=>Array.from(part)[0]||'').slice(0,2).join('').toUpperCase())}</span>`;
const placeIcon = id => `<span class="place-icon ${esc(place(id)?.color)}">${icon({grocery:'bag',print:'print',library:'book',canteen:'cup'}[id])}</span>`;
const statusNames={awaiting:'Waiting for replies',active:'Ready to go',completed:'Circle complete',cancelled:'Cancelled',expired:'Expired',needs_handoff:'Handover needs attention'};
const pill=status=>`<span class="pill ${esc(status)}">${esc(statusNames[status]||status)}</span>`;

function notify(message){const el=$('#toast');el.textContent=message;el.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,4500);}
async function api(path, data){
  const response=await fetch(path,{method:data?'POST':'GET',headers:{'Content-Type':'application/json','X-Demo-Member':actor},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(15000)});
  const result=await response.json();
  if(response.status===401){window.location.reload();throw new Error(result.error);}
  if(!response.ok){const error=new Error(result.error||'Something went wrong. Please try again.');error.status=response.status;throw error;}
  return result;
}
async function refresh(force=false){
  try{
    const next=await api('/api/board');
    const changed=!state || next.version!==state.version || next.actor!==state.actor;
    state=next;if(live)actor=next.actor;connected=true;$('#connection').hidden=true;
    if(changed||force){render();if(dialogState?.kind==='loop')showLoop(dialogState.id,false);else if(dialogState?.kind==='match'){const id=dialogState.id;if(state.matching.candidates.some(c=>c.id===id))showMatch(id);else{closeModal();notify('The board changed. Please review the latest suggestions.');}}}
  }catch(error){
    connected=false;$('#connection').textContent='The server is unavailable. Your saved board is preserved. Try refreshing in a moment.';$('#connection').hidden=false;
    if(!state)$('#app').innerHTML=`<div class="empty"><h3>We couldn’t open the board.</h3><p>Make sure ErrandLoop is running, then try again.</p><button class="button primary" data-action="refresh">Try again</button></div>`;
  }
}
async function act(command, extra={}, options={}){
  if(saving)return false;
  saving=true;
  document.querySelectorAll('[data-mutation],#post-form button[type=submit]').forEach(b=>b.disabled=true);
  try{
    state=await api('/api/actions/'+command,{version:state.version,operation:crypto.randomUUID(),...extra});
    if(options.close!==false)closeModal();
    render();
    if(options.close===false&&dialogState?.kind==='loop')showLoop(dialogState.id,false);
    notify(options.message||'Saved. The board is up to date.');
    return true;
  }catch(error){
    if(error.status===409){await refresh(true);}
    const errorBox=$('#form-error');
    if(errorBox){errorBox.textContent=error.message;errorBox.focus();}else notify(error.message);
    return false;
  }finally{saving=false;document.querySelectorAll('[data-mutation],#post-form button[type=submit]').forEach(b=>b.disabled=false);}
}
function render(){
  const currentMembers=state.members.map(m=>`<option value="${esc(m.id)}"${m.id===actor?' selected':''}>${esc(m.name)}</option>`).join('');
  $('#actor').innerHTML=live?`<option>${esc(member(actor).name)}</option>`:currentMembers;
  $('#actor').disabled=live;
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===currentView));
  $('#loop-count').textContent=state.loops.filter(l=>l.members.includes(actor)&&['awaiting','active','needs_handoff'].includes(l.status)).length;
  $('#app').innerHTML=currentView==='board'?renderBoard():currentView==='loops'?renderLoops():renderActivity();
}
function intro(title, subtitle, buttons=true){return `<section class="page-intro"><div><div class="eyebrow">${icon('pin',13)} ${esc(state.group?.name || 'The Courtyard')} <span aria-hidden="true">/</span> ${live?'Your group':'Campus circle'}</div><h1>${title}</h1><p>${subtitle}</p></div>${buttons?`<div class="actions"><button class="button" data-action="add-request">${icon('bag')}I need a hand</button><button class="button primary" data-action="add-trip">${icon('plus')}I’m heading out</button></div>`:''}</section>`;}
function renderBoard(){
  const candidates=state.matching.candidates.filter(c=>c.members.includes(actor));
  const candidate=candidates.find(c=>c.recommended)||candidates[0];
  const active=state.loops.find(l=>l.members.includes(actor)&&['awaiting','active','needs_handoff'].includes(l.status));
  const open=state[boardTab].filter(x=>x.status==='open'&&(destination==='all'||x.destination===destination));
  const reason=state.matching.unmatched.find(x=>x.member===actor);
  const setup=setupSteps();
  return `${intro('Going anyway?', 'Turn your next trip into a little help for someone nearby.')}
    <div class="layout"><section aria-label="Community board">${setup}${candidate||active||!setup?feature(candidate,active):''}
      <div class="section-top"><h2>Around your group</h2><span>${state.members.length} ${live?(state.members.length===1?'member':'members'):'demo neighbours'}</span></div>
      <div class="filters"><div class="tabs" role="tablist" aria-label="Board posts"><button class="tab ${boardTab==='trips'?'active':''}" role="tab" aria-selected="${boardTab==='trips'}" data-tab="trips">Heading out <span>${state.trips.filter(t=>t.status==='open').length}</span></button><button class="tab ${boardTab==='requests'?'active':''}" role="tab" aria-selected="${boardTab==='requests'}" data-tab="requests">Need a hand <span>${state.requests.filter(r=>r.status==='open').length}</span></button></div>
      <select class="filter-select" id="place-filter" aria-label="Filter by destination"><option value="all">Everywhere nearby</option>${state.places.map(p=>`<option value="${esc(p.id)}" ${destination===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></div>
      <div class="cards" role="tabpanel">${open.length?open.map(card).join(''):`<div class="empty"><h3>No open ${boardTab==='trips'?'trips':'requests'} here yet.</h3><p>${destination!=='all'?'Try another destination to see more posts.':state.members.length===1?'Your neighbours’ plans will appear here once they join.':'Be the first to share a planned stop or pickup request.'}</p><button class="button" data-action="add-${boardTab==='trips'?'trip':'request'}">${icon('plus')}${boardTab==='trips'?'Post a trip':'Ask for a pickup'}</button></div>`}</div>
      ${reason?`<div class="match-reasons">${icon('info',17)}<span><strong>Still looking for your circle.</strong> ${esc(reason.reason)} <button class="subtle-link" data-action="match-help">See what needs to fit ↗</button></span></div>`:''}
    </section><aside class="side-column" aria-label="Your posts and group summary">${pocket()}${progressCard()}
      ${state.matching.potentialTripsAvoided>0?`<div class="side-card community-card"><div class="eyebrow">A little goes a long way</div><div class="avatars">${state.members.slice(1,5).map(m=>avatar(m.id)).join('')}</div><div class="community-number">${state.matching.potentialTripsAvoided}</div><p>extra pickup trips could be avoided with the suggested circles.</p><small>Assumes one separate pickup trip per request. This is an estimate, not a measured saving.</small></div>`:''}
      <div class="quiet-note"><strong>${icon('loop',16)} A favour comes full circle.</strong>You help one neighbour. Another helps you. Everyone says yes before anyone sets off.<br><button class="subtle-link" data-action="guide">See how it works ↗</button></div>
    </aside></div>`;
}
function setupSteps(){
  const ownTrip=state.trips.some(t=>t.member===actor&&['open','reserved','active'].includes(t.status));
  const ownRequest=state.requests.some(r=>r.member===actor&&['open','reserved','active'].includes(r.status));
  if(!live||state.loops.some(l=>l.members.includes(actor))||(ownTrip&&ownRequest&&state.members.length>1))return '';
  const steps=[{done:state.members.length>1,label:'Invite a neighbour',action:'group',detail:'Use Your group to share the invitation code.'},{done:ownTrip,label:'Post your planned trip',action:'add-trip',detail:'Where are you already going?'},{done:ownRequest,label:'Ask for a pickup',action:'add-request',detail:'What do you need from another stop?'}];
  const next=steps.find(step=>!step.done);
  const count=steps.filter(step=>step.done).length;
  return `<section class="setup-steps" aria-label="Your first circle"><div class="setup-heading"><div class="eyebrow">Your first circle</div><span class="setup-count">${count} of 3 ready</span></div><h2>Give a hand. Get a hand.</h2><p>Start with your own plans. Each neighbour needs a trip and a pickup request.</p><ol class="setup-grid">${steps.map((step,i)=>`<li class="setup-step ${step.done?'done':step===next?'current':''}"><span aria-hidden="true">${step.done?'✓':i+1}</span><strong>${step.label}${step.done?' — done':''}</strong><p>${step.detail}</p></li>`).join('')}</ol><div class="setup-next"><button class="button primary" data-action="${next.action}">${next.label} ${icon('arrow')}</button><span>You can complete these in any order.</span></div></section>`;
}
function progressCard(){
  const pending=state.loops.filter(l=>['awaiting','active','needs_handoff'].includes(l.status)).length;
  if(!pending&&!state.metrics.handovers&&!state.metrics.completed)return `<div class="side-card first-handover"><div class="eyebrow">From plan to pickup</div><h3>Your first handover starts here.</h3><p>Review a match, agree together, then confirm when your item reaches you.</p><button class="subtle-link" data-action="guide">See the three steps ↗</button></div>`;
  return `<div class="side-card"><div class="eyebrow">Promises into pickups</div><h3>What actually happened</h3><div class="progress-counts"><div><strong>${state.metrics.handovers}</strong><span>receiver-confirmed handovers</span></div><div><strong>${state.metrics.completed}</strong><span>completed circles</span></div></div><p class="guide-sub">${pending} circles in progress. Confirmations are reported by members; they do not measure distance, money, or emissions saved.</p><button class="subtle-link" data-view="activity">See the activity record ↗</button></div>`;
}
function matchProof(c){
  return `<section class="match-proof" aria-label="Why this circle fits"><div class="eyebrow">Why this circle fits</div><h3>Every promise has a place.</h3>${c.members.length>2&&!state.matching.candidates.some(other=>other.members.length===2&&other.members.every(m=>c.members.includes(m)))?'<div class="callout">A pair swap cannot do this. No two people in this circle have compatible two-way pickups; helping around the circle makes the exchange possible.</div>':''}<p>Each member collects once and receives once. These checks use the times and places your group posted.</p>${c.edges.map(e=>{
    const t=state.trips.find(t=>t.id===e.trip),r=state.requests.find(r=>r.id===e.request);
    const margin=Math.floor((e.deadline-e.returns)/60);
    return `<article class="proof-row"><strong>${esc(name(e.giver))} → ${esc(name(e.receiver))}</strong><dl><div><dt>Existing stop</dt><dd>${esc(place(e.destination).name)}</dd></div><div><dt>Pickup ready</dt><dd>${time(r.ready)} · before departure at ${time(e.depart)}</dd></div><div><dt>Carrying space</dt><dd>${e.units} of ${t.capacity} spaces needed</dd></div><div><dt>Deadline margin</dt><dd>${margin} min between planned return and deadline</dd></div></dl></article>`;
  }).join('')}<p class="guide-sub">${c.recommended?'This belongs to the recommended set of non-overlapping circles, selected to help the most members. Ties favour earlier total returns.':'This is a valid alternative; it may share members with another suggestion.'} Travel routes and delays are not verified. Confirm the handover plan together.</p></section>`;
}
function feature(c,active){
  const completed=state.loops.find(l=>l.status==='completed'&&l.members.includes(actor));
  const hasOpen=state.trips.some(t=>t.member===actor&&t.status==='open')||state.requests.some(r=>r.member===actor&&r.status==='open');
  if(!c&&!active&&completed&&!hasOpen){return `<section class="feature"><div><div class="eyebrow">${icon('check',16)} Every handover confirmed</div><h2>You closed the circle.</h2><p>${completed.members.length} neighbours helped one another. Your completed posts are saved in My circles; the board is ready for your next trip.</p><button class="button lime" data-action="loop" data-id="${completed.id}">View completed exchange ${icon('arrow')}</button><p class="guide-sub">Confirmation records are reported by participants.</p></div>${cyclePicture(completed)}</section>`;}

  if(active){return `<section class="feature"><div><div class="eyebrow">Your circle is taking shape</div><h2>${active.status==='active'?'Everyone’s in.':active.status==='needs_handoff'?'Let’s finish<br>the handovers.':'A little help,<br>coming together.'}</h2><p>${active.status==='awaiting'?`${active.accepted.length} of ${active.members.length} neighbours have accepted. Everyone’s consent comes first.`:active.status==='active'?'Your pickups are agreed. Keep your neighbours updated as you go.':'An item was already collected. Your existing handovers stay visible.'}</p><button class="button lime" data-action="loop" data-id="${active.id}">Open your circle ${icon('arrow')}</button></div>${cyclePicture(active)}</section>`;}
  if(c){return `<section class="feature"><div><div class="eyebrow">${icon('loop',15)} A ${c.members.length}-person circle fits</div><h2>Your trip.<br>Someone’s day made.</h2><p>You can help ${esc(name(c.edges.find(e=>e.giver===actor).receiver))}. ${esc(name(c.edges.find(e=>e.receiver===actor).giver))} can help you. The whole circle fits.</p><button class="button lime" data-action="match" data-id="${c.id}">Review this circle ${icon('arrow')}</button><br><span class="feature-tag">Review first. Nothing is agreed until everyone accepts.</span></div>${cyclePicture(c)}</section>`;}
  return `<section class="feature"><div><div class="eyebrow">Good things start small</div><h2>One trip.<br>A chance to help.</h2><p>Post where you’re going and what you need. We’ll look for a circle that works for everyone.</p><button class="button lime" data-action="add-trip">Post your trip ${icon('arrow')}</button></div><div class="cycle-picture"><div class="cycle-person n0">${avatar(actor)}<strong>${esc(name(actor))}</strong><small>Your next small favour</small></div></div></section>`;
}
function cyclePicture(c){
  const ordered=[];
  let giver=c.members.includes(actor)?actor:c.members[0];
  for(let i=0;i<c.edges.length;i++){
    const edge=c.edges.find(e=>e.giver===giver);
    if(!edge||ordered.includes(edge))break;
    ordered.push(edge);giver=edge.receiver;
  }
  const collect=c.edges.find(e=>e.giver===actor), receive=c.edges.find(e=>e.receiver===actor);
  const responsibility=collect&&receive?`<div class="your-exchange"><div><span>You collect for ${esc(name(collect.receiver))}</span><strong>${esc(collect.item)}</strong><small>From ${esc(place(collect.destination).name)}</small></div><div><span>You receive from ${esc(name(receive.giver))}</span><strong>${esc(receive.item)}</strong><small>Meet at ${esc(state.group?.meeting||'your agreed handover point')}</small></div></div>`:'';
  return `<section class="exchange-map" aria-label="Who collects for whom"><div class="exchange-map-heading"><span>THE EXCHANGE</span><span>${c.members.length} neighbours · one circle</span></div><ol>${ordered.map((e,i)=>`<li><div class="map-number" aria-hidden="true">${String(i+1).padStart(2,'0')}</div><div class="map-route"><div class="map-people"><strong>${esc(name(e.giver))}</strong><span class="map-arrow" aria-label="collects for">→</span><strong>${esc(name(e.receiver))}</strong></div><div class="map-location">${esc(place(e.destination).name)}</div><div class="map-item">${esc(e.item)}</div></div></li>`).join('')}</ol>${responsibility}<div class="map-footer">${icon('loop',15)} ${c.status==='completed'?'All recipients confirmed receipt.':'A circle means everyone collects once and receives once.'}</div></section>`;
}
// Keep dynamic diagram positioning in a stylesheet (no inline style attributes).
function layoutCycle(){
  document.querySelectorAll('.cycle-picture').forEach(el=>{const people=[...el.querySelectorAll('[data-point]')],n=people.length;people.forEach((p,i)=>{p.classList.add(`ring-${n}-${i}`);});});
}
function card(post){
  const trip='depart' in post, p=place(post.destination), m=member(post.member);
  return `<article class="trip-card"><div class="card-person">${avatar(m.id)}<div>${esc(name(m.id))}<small>${esc(m.room)}</small></div>${m.id===actor?'<span class="my-tag">YOURS</span>':''}</div><div class="destination">${placeIcon(p.id)}${esc(p.name)}</div><p class="card-note">${esc(trip?post.note:post.item)}</p><div class="card-bottom"><span>${icon(trip?'clock':'bag',14)} ${trip?`Leaves in ${relative(post.depart)}`:`${post.units} bag space${post.units>1?'s':''}`}</span><button data-action="post" data-id="${post.id}">Details ↗</button></div></article>`;
}
function pocket(){
  const ownTrip=state.trips.find(t=>t.member===actor&&['open','reserved','active'].includes(t.status));
  const ownNeed=state.requests.find(r=>r.member===actor&&['open','reserved','active'].includes(r.status));
  return `<div class="side-card"><h3>Your pocket <span aria-hidden="true">↘</span></h3>${ownTrip?`<div class="pocket-row">${placeIcon(ownTrip.destination)}<div><div class="overline">You’re heading to</div><strong>${esc(place(ownTrip.destination).name)}</strong><small>${time(ownTrip.depart)} – ${time(ownTrip.returns)}</small><small>${ownTrip.capacity} small-item space${ownTrip.capacity===1?'':'s'}</small></div></div><button class="subtle-link" data-action="post" data-id="${ownTrip.id}">View your trip</button>`:`<p class="card-note">No trip yet. Use “I’m heading out” to add your planned stop.</p>`}<div class="pocket-divider"></div>${ownNeed?`<div class="pocket-row">${icon('bag',21)}<div><div class="overline">You need a hand with</div><strong>${esc(ownNeed.item)}</strong><small>By ${time(ownNeed.deadline)}</small></div></div><button class="subtle-link" data-action="post" data-id="${ownNeed.id}">View your request</button>`:`<p class="card-note">No request yet. Use “I need a hand” to ask for a pickup.</p>`}</div>`;
}
function renderLoops(){
  const loops=state.loops.filter(l=>l.members.includes(actor));
  const suggestions=state.matching.candidates.filter(l=>l.members.includes(actor));
  return `${intro('Good things, in motion.', 'Every circle starts with a yes and ends with a confirmed handover.',false)}
    ${loops.length?`<div class="circle-list">${loops.map(l=>`<article class="circle-card"><div class="circle-card-top"><div class="avatars">${l.members.map(avatar).join('')}</div>${pill(l.status)}</div><h3>${l.members.length} neighbours. One circle.</h3><p>${l.edges.filter(e=>e.received).length} of ${l.edges.length} handovers confirmed · ${l.accepted.length} accepted</p><button class="button primary" data-action="loop" data-id="${l.id}">View circle ${icon('arrow')}</button></article>`).join('')}</div>`:`<div class="empty"><h3>Your first circle is waiting to happen.</h3><p>Review a suggestion on the board. Proposing a circle also confirms that you’re happy to take your part.</p><button class="button primary" data-action="go-board">Find a circle</button></div>`}
    ${suggestions.length?`<div class="section-top"><h2>Other ways to close the loop</h2><span>Alternatives may share participants</span></div><div class="circle-list">${suggestions.slice(0,8).map(c=>`<article class="circle-card"><div class="circle-card-top"><div class="avatars">${c.members.map(avatar).join('')}</div><span class="pill">${c.recommended?'Best group fit':'Alternative'}</span></div><h3>${c.members.map(m=>esc(name(m))).join(', ')}</h3><p>${c.members.length} requests fit existing stops, time windows, and bag space.</p><button class="button" data-action="match" data-id="${c.id}">Review exchange ${icon('arrow')}</button></article>`).join('')}</div>`:''}`;
}
function renderActivity(){return `${intro('The little things add up.', 'A shared record of promises kept, changes made, and circles completed.',false)}<div class="actions"><button class="button small" data-action="export">Download activity record</button></div><div class="activity-list">${state.activity.length?state.activity.map(a=>`<article class="activity-row">${avatar(a.member)}<div><p><strong>${esc(a.member==='system'?'ErrandLoop':member(a.member).name)}</strong></p><small>${esc(a.message)}</small></div><time>${time(a.at)}</time></article>`).join(''):`<div class="empty"><h3>A fresh page.</h3><p>Propose a circle or add a post. Its progress will appear here.</p></div>`}</div>`;}
function openModal(title, eyebrow, body, kind, id, focus=true){
  if(!modal.open)lastFocus=document.activeElement;
  const focused=modal.contains(document.activeElement)?document.activeElement:null;
  const focusAction=focused?.dataset.action, focusRequest=focused?.dataset.request;
  dialogState={kind,id};
  $('#modal-content').innerHTML=`<div class="modal-head"><div><div class="eyebrow">${eyebrow}</div><h2 id="dialog-title">${title}</h2></div><button class="close" data-action="close" aria-label="Close dialog">×</button></div><div class="modal-body">${body}</div>`;
  if(!modal.open)modal.showModal();
  else if(focus)$('#modal-content button')?.focus();
  else if(focused){
    const replacement=[...modal.querySelectorAll('[data-action]')].find(el=>el.dataset.action===focusAction&&el.dataset.request===focusRequest);
    (replacement||$('#modal-content button'))?.focus();
  }
}
function closeModal(){dialogState=null;modal.close();if(lastFocus?.isConnected)lastFocus.focus();}
function edgesHTML(c, progress=false){return c.edges.map(e=>`<div class="exchange-edge"><div class="edge-people">${avatar(e.giver)}<strong>${esc(name(e.giver))}</strong><span class="edge-arrow">collects for →</span>${avatar(e.receiver)}<strong>${esc(name(e.receiver))}</strong></div><h3>${esc(e.item)}</h3><p>${esc(place(e.destination).name)} · Return by ${time(e.returns)} · Needed by ${time(e.deadline)}</p>${progress?`<div class="edge-status">${e.received?`${icon('check',14)} Received and confirmed`:e.collected?'Collected · waiting for receiver confirmation':'Awaiting collection'}</div>${['active','needs_handoff'].includes(c.status)?`<div class="actions">${e.giver===actor&&!e.collected?`<button class="button small" data-mutation data-action="collected" data-id="${c.id}" data-request="${e.request}">I’ve collected this</button>`:''}${e.receiver===actor&&e.collected&&!e.received?`<button class="button small primary" data-mutation data-action="received" data-id="${c.id}" data-request="${e.request}">I’ve received this</button>`:''}</div>`:''}`:''}</div>`).join('');}
function showMatchHelp(){
  const reason=state.matching.unmatched.find(x=>x.member===actor);
  if(!reason){notify('Your matching status changed. Review the board.');return;}
  const request=state.requests.find(r=>r.id===reason.request);
  openModal('What is missing from your circle?','Matching explained',
    `<p>${esc(reason.reason)}</p><div class="callout guide-sub">Your pickup: <strong>${esc(request.item)}</strong> at ${esc(place(request.destination).name)}. Ready ${time(request.ready)}, needed by ${time(request.deadline)}.</div>
    ${(reason.checks||[]).map(check=>`<article class="proof-row"><h3>${esc(name(check.member))}’s planned trip</h3>${check.pickupFits?'<p>Pickup timing and space fit. Both people still need a reciprocal circle and everyone’s consent.</p>':`<ul>${check.blockers.map(b=>`<li>${esc(b)}</li>`).join('')}</ul>`}</article>`).join('')}
    <p class="guide-sub">Only change a time or item size if your actual plans allow it. Open posts can be removed and reposted from Your pocket. Matching never changes your commitments automatically.</p><button class="button primary" data-action="close">Back to my board</button>`, 'match-help');
}
function showMatch(id){
  const c=state.matching.candidates.find(c=>c.id===id);if(!c){notify('This suggestion changed. Please refresh the board.');return;}
  openModal('A little help, all the way round.',`${c.members.length} neighbours · One exchange`,
    `<p>Here’s exactly who collects what. Nothing is agreed until every neighbour accepts.</p>${edgesHTML(c)}${matchProof(c)}<div class="check-list"><span>${icon('check',15)}Same planned stops</span><span>${icon('check',15)}Deadlines fit</span><span>${icon('check',15)}Bag space checked</span></div><div class="callout guide-sub">Handovers: ${esc(state.group?.meeting || 'the courtyard')}. Pickups must be prepared and paid for, with collection permission arranged separately.</div><div class="actions"><button class="button primary full" data-mutation data-action="propose" data-id="${id}">I’m in — propose this circle ${icon('arrow')}</button></div><p class="guide-sub">This reserves everyone’s posts while they decide. Unaccepted circles expire at the first departure.</p>`, 'match',id);
}
function showLoop(id,focus=true){
  const l=state.loops.find(l=>l.id===id);if(!l){closeModal();return;}
  const myPickup=l.edges.find(e=>e.giver===actor), myReceipt=l.edges.find(e=>e.receiver===actor);
  const nextStep=l.status==='awaiting'?(!l.accepted.includes(actor)?'Review your part and accept only if you can make the trip.':'Wait for every neighbour to accept before collecting.'):['active','needs_handoff'].includes(l.status)?(!myPickup.collected?'Your next step: collect '+myPickup.item+' for '+name(myPickup.receiver)+'.':myReceipt.collected&&!myReceipt.received?'Your next step: confirm receipt only after you have your item.':!myReceipt.collected?'Your pickup is recorded. Wait for your neighbour to collect your item.':'Your part is recorded. Other handovers are still pending.'):'';
  const stages=[{label:'Agree',done:l.members.every(m=>l.accepted.includes(m))},{label:'Collect',done:l.edges.every(e=>e.collected)},{label:'Hand over',done:l.edges.every(e=>e.received)}];
  const currentStage=stages.findIndex(stage=>!stage.done);
  const journey=`<ol class="exchange-journey" aria-label="Exchange progress">${stages.map((stage,i)=>`<li class="${stage.done?'done':i===currentStage?'current':''}" ${i===currentStage?'aria-current="step"':''}><span aria-hidden="true">${stage.done?'✓':i+1}</span>${stage.label}<small>${stage.done?'Complete':i===currentStage?'Current step':'Up next'}</small></li>`).join('')}</ol>`;
  openModal('Your circle, one step at a time.' ,statusNames[l.status],
    `${journey}${l.status==='needs_handoff'?'<div class="callout warning">Someone reported a problem after collection. Items already collected must still be handed over. Contact your group; these posts will not be rematched automatically.</div>':''}
    <div class="acceptance">${l.members.map(m=>`<span class="${l.accepted.includes(m)?'yes':''}">${l.accepted.includes(m)?'✓':'○'} ${esc(name(m))}</span>`).join('')}</div>${nextStep?`<div class="callout next-step" role="status">${esc(nextStep)}</div>`:''}${edgesHTML(l,true)}
    ${l.status==='awaiting'?`<div class="actions">${!l.accepted.includes(actor)?`<button class="button primary" data-mutation data-action="accept" data-id="${id}">Yes, I’m in ${icon('check')}</button><button class="button" data-mutation data-action="decline" data-id="${id}">Decline</button>`:'<p class="guide-sub">You’ve accepted. Waiting for the others.</p>'}</div><p class="guide-sub">Everyone must accept before ${time(l.expires)}.</p>`:''}
    ${['awaiting','active'].includes(l.status)?`<button class="subtle-link" data-action="cancel-loop-prompt" data-id="${id}">I can’t make this trip</button>`:''}
    ${l.status==='completed'?'<div class="callout">Every receiver confirmed their item. This circle is complete. Thanks for helping it happen.</div>':''}
    ${live ? '' : `<div class="pocket-divider"></div><div class="guide-sub"><strong>Demo controls</strong> · Play another participant to test their consent and handover.<div class="actions">${l.members.filter(m=>m!==actor).map(m=>`<button class="button small" data-action="switch" data-member="${m}" data-loop="${id}">Continue as ${esc(member(m).name)}</button>`).join('')}</div></div>`}`, 'loop',id,focus);
}
function showPost(id){
  const p=[...state.trips,...state.requests].find(p=>p.id===id);if(!p)return;
  const trip='depart' in p;
  openModal(trip?esc(place(p.destination).name):esc(p.item),`${esc(name(p.member))} · ${trip?'Planned trip':'Pickup request'}`,
    `<p>${esc(p.note)}</p><div class="callout">${trip?`Leaves at ${time(p.depart)} · Returns by ${time(p.returns)}<br>Room for ${p.capacity} small item${p.capacity===1?'':'s'}.`:`Ready at ${time(p.ready)} · Needed by ${time(p.deadline)}<br>${p.units} small-item space${p.units>1?'s':''} · ${esc(place(p.destination).name)}`}</div><p class="guide-sub">Status: ${esc(p.status)}. A small-item space is a rough carrying estimate agreed by your group.</p>${p.member===actor&&p.status==='open'?`<div class="actions"><button class="button danger" data-mutation data-action="cancel-post" data-id="${p.id}">Remove this ${trip?'trip':'request'}</button></div>`:''}${p.status==='reserved'||p.status==='active'?'<p class="guide-sub">This post is in a circle. Open My circles to manage it.</p>':''}`, 'post',id);
}
function localDate(ts){const d=new Date(ts*1000);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}T${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;}
function showForm(type){
  const existing=state[type==='trip'?'trips':'requests'].find(p=>p.member===actor&&['open','reserved','active'].includes(p.status));
  if(existing){showPost(existing.id);notify(`You already have a ${type}. Remove or finish it before adding another.`);return;}
  const now=Math.floor(Date.now()/1000), places=state.places.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  openModal(type==='trip'?'Where are you heading?':'What can someone pick up?',`${esc(name(actor))} · A small favour`,
    `<form id="post-form" data-type="${type}"><div class="form-error" id="form-error" role="alert" tabindex="-1"></div><div class="form-grid"><label class="field full">${type==='trip'?'I’m already going to':'Pickup location'}<select name="destination" required>${places}</select></label>
    ${type==='request'?'<label class="field full">What needs collecting?<input name="item" required maxlength="90" placeholder="e.g. My prepaid assignment printout"><small>Prepared collections only. Arrange payment and pickup permission separately.</small></label>':''}
    ${type==='trip'?`<label class="field">Leaving at<input type="datetime-local" name="depart" required value="${localDate(now+1800)}" min="${localDate(now+60)}" max="${localDate(now+86400)}"></label><label class="field">Back at handover point by<input type="datetime-local" name="returns" required value="${localDate(now+3600)}" min="${localDate(now+120)}" max="${localDate(now+86400)}"></label>`:`<label class="field">Ready for pickup at<input type="datetime-local" name="ready" required value="${localDate(now)}"></label><label class="field">I need it by<input type="datetime-local" name="deadline" required value="${localDate(now+7200)}" min="${localDate(now+60)}" max="${localDate(now+86400)}"></label>`}
    <label class="field full">${type==='trip'?'Space I can offer':'Space this needs'}<select name="${type==='trip'?'capacity':'units'}">${[1,2,3,4,5].map(n=>`<option value="${n}">${n} small item${n>1?'s':''}</option>`).join('')}</select><small>Think a paperback, document envelope, or small prepared package per space.</small></label><label class="field full">A note for your neighbour<textarea name="note" maxlength="180" placeholder="Collection details, item size, or anything useful."></textarea></label></div><div class="actions"><button class="button primary full" type="submit">Post ${type==='trip'?'my trip':'my request'} ${icon('arrow')}</button></div><p class="guide-sub">One active trip and one active request per person. Exact existing destinations only; no detours.</p></form>`, 'form',type);
}
function guide(){if(live){openModal('Help that comes back around.','How circles work',`<p>Imagine you are going to the shop and need a library pickup. A neighbour is going to the library and needs something from the shop. Your existing trips can help each other.</p><ol class="how-steps"><li><strong>Post both sides.</strong> Add your planned trip and one pickup request. Use the same group locations.</li><li><strong>Review a circle.</strong> We check ready times, return deadlines and carrying space for two to four people.</li><li><strong>Everyone decides.</strong> A proposal reserves posts. Collection starts only after everyone accepts.</li><li><strong>Close the loop.</strong> Collectors mark pickups; recipients confirm their own receipt.</li></ol><div class="callout">Plans changed? Cancel from your circle. If an item was already collected, its handover stays visible so it is not assigned to someone else.</div><p class="guide-sub">Prepared, prepaid pickups only. Arrange permission and handover details with people you know.</p>`,'guide');return;}openModal('A favour comes full circle.','The 2-minute walkthrough',
  `<p>ErrandLoop looks for exchanges among trips people already planned. Each person helps a neighbour and receives help from the next.</p><div class="step"><span class="step-num">1</span><div><p><strong>Start in Sana’s demo seat.</strong></p><small>Sana appears as “You” in this seat. Her grocery trip and printout request are already posted.</small></div></div><div class="step"><span class="step-num">2</span><div><p><strong>Review and propose the suggested circle.</strong></p><small>You collect Ravi’s coffee. Asha collects your printout. Ravi collects Asha’s book.</small></div></div><div class="step"><span class="step-num">3</span><div><p><strong>Take Asha’s seat, then Ravi’s.</strong></p><small>Use the demo switcher. Both must accept their own part before the circle activates.</small></div></div><div class="step"><span class="step-num">4</span><div><p><strong>Collect, hand over, and close the circle.</strong></p><small>Only the collector marks an item collected. Only its receiver confirms receipt. Try cancelling before and after collection.</small></div></div><div class="callout guide-sub">For a blank start, take Kabir’s seat and post your own trip and request. “Start fresh” restores the fictional board with new future times.</div><p class="guide-sub">This is a single-group demo. Switching seats is a demonstration feature, not a real sign-in system. No money changes hands in the app, and no live location is tracked.</p><div class="actions"><button class="button primary full" data-action="close">Let’s find a circle ${icon('arrow')}</button></div>`, 'guide');}

document.addEventListener('click', async event=>{
  const button=event.target.closest('button');if(!button||button.disabled)return;
  if(button.dataset.action==='sign-out'){await api('/api/logout',{});window.location.reload();return;}
  if(!state&&button.dataset.action!=='guide'&&button.dataset.action!=='close'&&button.dataset.action!=='refresh')return;
  if(button.dataset.view){currentView=button.dataset.view;render();return;}
  if(button.dataset.tab){boardTab=button.dataset.tab;render();return;}
  const {action,id}=button.dataset;
  if(action==='close')closeModal();
  else if(action==='guide')guide();
  else if(action==='group')showGroup();
  else if(action==='copy-invite'){try{await navigator.clipboard.writeText(location.origin+'/#join='+encodeURIComponent(state.group.id));notify('Invitation link copied. Share privately with people you know.');}catch(e){notify('Select and copy the invitation link shown above.');}}
  else if(action==='copy-group'){try{await navigator.clipboard.writeText(state.group.id);notify('Group code copied. Share it privately with your neighbours.');}catch(e){notify('Select and copy the group code shown above.');}}
  else if(action==='refresh')await refresh(true);
  else if(action==='go-board'){currentView='board';render();}
  else if(action==='add-trip')showForm('trip');
  else if(action==='add-request')showForm('request');
  else if(action==='match')showMatch(id);
  else if(action==='match-help')showMatchHelp();
  else if(action==='loop')showLoop(id);
  else if(action==='post')showPost(id);
  else if(action==='propose'){
    const ok=await act('propose',{id},{message:'Circle proposed. Now your neighbours can decide.'});
    if(ok){currentView='loops';render();showLoop(state.loops.find(l=>l.members.includes(actor)&&l.status==='awaiting').id);}
  }
  else if(['accept','decline','collected','received'].includes(action))await act(action,{id,request:button.dataset.request},{close:false,message:action==='received'?'Handover confirmed. Thank you!':'Your update is saved.'});
  else if(action==='cancel-post')await act('cancel_post',{id},{message:'Post removed. You can add a new one.'});
  else if(action==='cancel-loop-prompt')openModal('Can’t make this trip?','Plans change',`<p>Before any collection, your trip is removed and other available posts return to the board. If something is already collected, the circle stays open for handover and is not automatically rematched.</p><div class="actions"><button class="button danger" data-mutation data-action="cancel-loop" data-id="${id}">Confirm I can’t make it</button><button class="button" data-action="loop" data-id="${id}">Keep my place</button></div>`,'cancel',id);
  else if(action==='cancel-loop')await act('cancel_loop',{id},{message:'The circle has been updated. Check its handover status.'});
  else if(action==='switch'){
    actor=button.dataset.member;localStorage.setItem('errandloop-actor',actor);await refresh(true);showLoop(button.dataset.loop);notify(`You’re now playing ${member(actor).name}.`);
  }
  else if(action==='reset-prompt')openModal('A fresh board?','Reset the demo','<p>This clears the shared demo board’s posts, circles, and activity, then restores the sample group with fresh times.</p><div class="actions"><button class="button danger" data-action="reset">Reset the demo</button><button class="button" data-action="close">Keep the board</button></div>','reset');
  else if(action==='reset'){
    try{state=await api('/api/reset',{});actor='you';localStorage.setItem('errandloop-actor',actor);currentView='board';destination='all';boardTab='trips';closeModal();await refresh(true);notify('Fresh board, fresh opportunities.');}catch(e){notify(e.message);}
  }
  else if(action==='export'){
    const report={app:'ErrandLoop',exportedAt:new Date().toISOString(),notice:live?'Group activity record; trip savings are estimates.':'Fictional campus demo. Not verified real-world impact.',loops:state.loops,activity:state.activity,metrics:state.metrics};
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='errandloop-activity.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
});
document.addEventListener('change',async event=>{
  if(event.target.id==='actor'&&!live){actor=event.target.value;localStorage.setItem('errandloop-actor',actor);closeModal();await refresh(true);}
  if(event.target.id==='place-filter'){destination=event.target.value;render();}
});
document.addEventListener('submit',async event=>{
  if(event.target.id==='place-form'){event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{state=await api('/api/places',{name:new FormData(event.target).get('name')});render();showGroup();notify('Pickup location added.');}catch(e){notify(e.message);button.disabled=false;}return;}
  if(event.target.id!=='post-form')return;
  event.preventDefault();const form=event.target, type=form.dataset.type, data=Object.fromEntries(new FormData(form));
  for(const key of ['depart','returns','ready','deadline'])if(data[key])data[key]=Math.floor(new Date(data[key]).getTime()/1000);
  for(const key of ['units','capacity'])if(data[key])data[key]=Number(data[key]);
  const invalid=type==='trip'&&data.returns<=data.depart?'Your return time must be after your departure.':type==='request'&&data.deadline<=data.ready?'Your pickup deadline must be after the item is ready.':'';
  if(invalid){const box=$('#form-error');box.textContent=invalid;box.focus();return;}
  await act(type,data,{message:'Posted. We’re looking for a circle that fits.'});
});
modal.addEventListener('cancel',()=>{dialogState=null;});
modal.addEventListener('click',e=>{if(e.target===modal){const r=modal.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeModal();}});
// The mutation observer only assigns diagram classes after a render.
new MutationObserver(layoutCycle).observe($('#app'),{childList:true,subtree:true});
await refresh(true);
setInterval(()=>{if(!document.hidden&&!saving)refresh();},15000);

function showGroup(){
  if(!live||!state)return;
  openModal(esc(state.group.name),'Your group',
    `<p>Invite people you know. Each person joins with this code and creates their own username and password.</p>
    <div class="callout"><strong>Group code</strong><p class="group-code">${esc(state.group.id)}</p><button class="button small" data-action="copy-group">Copy group code</button></div>
    <label class="field">Invitation link<input readonly aria-label="Invitation link" value="${esc(location.origin+'/#join='+encodeURIComponent(state.group.id))}"></label><button class="button small" data-action="copy-invite">Copy invitation link</button>
    ${['localhost','127.0.0.1','[::1]'].includes(location.hostname)?'<p class="guide-sub">This address works on this computer only. Use separate browser profiles here for a local trial. A public deployment is needed to invite people on other devices over the internet.</p>':''}
    <p><strong>Handover point:</strong> ${esc(state.group.meeting)}</p>
    <p>Post your actual trip and what you need collected. Matches appear when at least two members have compatible trips and requests. Each person must accept from their own account.</p>
    <h3>Pickup locations</h3><ul>${state.places.map(p=>`<li>${esc(p.name)}</li>`).join('')}</ul>
    ${state.group.owner===actor?'<form id="place-form"><label class="field">Add a pickup location<input name="name" required minlength="2" maxlength="60"></label><button class="button primary" type="submit">Add location</button></form>':''}
    <p class="guide-sub">${state.members.length}/16 members. Keep the group code for future sign-in. Password recovery and member removal are not available in this first version.</p>`, 'group');
}
