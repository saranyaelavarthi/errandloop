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
const avatar = id => `<span class="avatar ${esc(member(id).color)}">${esc(member(id).initials)}</span>`;
const placeIcon = id => `<span class="place-icon ${esc(place(id)?.color)}">${icon({grocery:'bag',print:'print',library:'book',canteen:'cup'}[id])}</span>`;
const statusNames={awaiting:'Waiting for replies',active:'Ready to go',completed:'Circle complete',cancelled:'Cancelled',expired:'Expired',needs_handoff:'Handover needs attention'};
const pill=status=>`<span class="pill ${esc(status)}">${esc(statusNames[status]||status)}</span>`;

function notify(message){const el=$('#toast');el.textContent=message;el.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,4500);}
async function api(path, data){
  const response=await fetch(path,{method:data?'POST':'GET',headers:{'Content-Type':'application/json','X-Demo-Member':actor},body:data?JSON.stringify(data):undefined});
  const result=await response.json();
  if(response.status===401){window.location.reload();throw new Error(result.error);}
  if(!response.ok){const error=new Error(result.error||'Something went wrong. Please try again.');error.status=response.status;throw error;}
  return result;
}
async function refresh(force=false){
  try{
    const next=await api('/api/board');
    const changed=!state || next.version!==state.version || next.actor!==state.actor;
    state=next;connected=true;$('#connection').hidden=true;
    if(changed||force){render();if(dialogState?.kind==='loop')showLoop(dialogState.id,false);}
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
  $('#actor').innerHTML=currentMembers;
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===currentView));
  $('#loop-count').textContent=state.loops.filter(l=>l.members.includes(actor)&&['awaiting','active','needs_handoff'].includes(l.status)).length;
  $('#app').innerHTML=currentView==='board'?renderBoard():currentView==='loops'?renderLoops():renderActivity();
}
function intro(title, subtitle, buttons=true){return `<section class="page-intro"><div><div class="eyebrow">${icon('pin',13)} The Courtyard <span aria-hidden="true">/</span> Campus circle</div><h1>${title}</h1><p>${subtitle}</p></div>${buttons?`<div class="actions"><button class="button" data-action="add-request">${icon('bag')}I need a hand</button><button class="button primary" data-action="add-trip">${icon('plus')}I’m heading out</button></div>`:''}</section>`;}
function renderBoard(){
  const candidates=state.matching.candidates.filter(c=>c.members.includes(actor));
  const candidate=candidates.find(c=>c.recommended)||candidates[0];
  const active=state.loops.find(l=>l.members.includes(actor)&&['awaiting','active','needs_handoff'].includes(l.status));
  const open=state[boardTab].filter(x=>x.status==='open'&&(destination==='all'||x.destination===destination));
  const reason=state.matching.unmatched.find(x=>x.member===actor);
  return `${intro('Going anyway?', 'Turn your next trip into a little help for someone nearby.')}
    <div class="layout"><section aria-label="Community board">${feature(candidate,active)}
      <div class="section-top"><h2>Around the courtyard</h2><span>${state.members.length} demo neighbours</span></div>
      <div class="filters"><div class="tabs" role="tablist" aria-label="Board posts"><button class="tab ${boardTab==='trips'?'active':''}" role="tab" aria-selected="${boardTab==='trips'}" data-tab="trips">Heading out <span>${state.trips.filter(t=>t.status==='open').length}</span></button><button class="tab ${boardTab==='requests'?'active':''}" role="tab" aria-selected="${boardTab==='requests'}" data-tab="requests">Need a hand <span>${state.requests.filter(r=>r.status==='open').length}</span></button></div>
      <select class="filter-select" id="place-filter" aria-label="Filter by destination"><option value="all">Everywhere nearby</option>${state.places.map(p=>`<option value="${esc(p.id)}" ${destination===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></div>
      <div class="cards" role="tabpanel">${open.length?open.map(card).join(''):`<div class="empty"><h3>No open ${boardTab==='trips'?'trips':'requests'} here yet.</h3><p>Try another destination, or add your own post.</p><button class="button" data-action="add-${boardTab==='trips'?'trip':'request'}">${icon('plus')}Add a post</button></div>`}</div>
      ${reason?`<div class="match-reasons">${icon('info',17)}<span><strong>Still looking for your circle.</strong> ${esc(reason.reason)}</span></div>`:''}
    </section><aside class="side-column" aria-label="Your posts and group summary">${pocket()}
      <div class="side-card community-card"><div class="eyebrow">A little goes a long way</div><div class="avatars">${state.members.slice(1,5).map(m=>avatar(m.id)).join('')}</div><div class="community-number">${state.matching.potentialTripsAvoided}</div><p>extra pickup trips could be avoided with the suggested circles.</p><small>Assumes one separate pickup trip per request. This is a demo estimate, not a measured saving.</small></div>
      <div class="quiet-note"><strong>${icon('loop',16)} A favour comes full circle.</strong>You help one neighbour. Another helps you. Everyone says yes before anyone sets off.<br><button class="subtle-link" data-action="guide">See how it works ↗</button></div>
    </aside></div>`;
}
function feature(c,active){
  if(active){return `<section class="feature"><div><div class="eyebrow">Your circle is taking shape</div><h2>${active.status==='active'?'Everyone’s in.':active.status==='needs_handoff'?'Let’s finish<br>the handovers.':'A little help,<br>coming together.'}</h2><p>${active.status==='awaiting'?`${active.accepted.length} of ${active.members.length} neighbours have accepted. Everyone’s consent comes first.`:active.status==='active'?'Your pickups are agreed. Keep your neighbours updated as you go.':'An item was already collected. Your existing handovers stay visible.'}</p><button class="button lime" data-action="loop" data-id="${active.id}">Open your circle ${icon('arrow')}</button></div>${cyclePicture(active)}</section>`;}
  if(c){return `<section class="feature"><div><div class="eyebrow">${icon('loop',15)} A ${c.members.length}-person circle fits</div><h2>Your trip.<br>Someone’s day made.</h2><p>You can help ${esc(name(c.edges.find(e=>e.giver===actor).receiver))}. ${esc(name(c.edges.find(e=>e.receiver===actor).giver))} can help you. The whole circle fits.</p><button class="button lime" data-action="match" data-id="${c.id}">Review this circle ${icon('arrow')}</button><br><span class="feature-tag">Existing stops only · No extra detours</span></div>${cyclePicture(c)}</section>`;}
  return `<section class="feature"><div><div class="eyebrow">Good things start small</div><h2>One trip.<br>A chance to help.</h2><p>Post where you’re going and what you need. We’ll look for a circle that works for everyone.</p><button class="button lime" data-action="add-trip">Post your trip ${icon('arrow')}</button></div><div class="cycle-picture"><div class="cycle-person n0">${avatar(actor)}<strong>${esc(name(actor))}</strong><small>Your next small favour</small></div></div></section>`;
}
function cyclePicture(c){
  const n=c.members.length;
  const points=c.members.map((m,i)=>{const a=2*Math.PI*i/n;return {m,x:115+75*Math.sin(a),y:90-67*Math.cos(a)};});
  const lines=points.map((p,i)=>{const q=points[(i+1)%n],dx=q.x-p.x,dy=q.y-p.y,len=Math.hypot(dx,dy);return `<path d="M${p.x+dx/len*30},${p.y+dy/len*30} L${q.x-dx/len*35},${q.y-dy/len*35}"/>`;}).join('');
  return `<div class="cycle-picture" role="img" aria-label="Exchange circle: ${esc(c.edges.map(e=>`${name(e.giver)} collects for ${name(e.receiver)}`).join('; '))}"><svg viewBox="0 0 230 220" aria-hidden="true"><defs><marker id="arrowhead" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="none" stroke="#b9d397" stroke-width="1.2"/></marker></defs><g fill="none" stroke="#92ad7d" stroke-width="1.3" stroke-dasharray="4 5" marker-end="url(#arrowhead)">${lines}</g></svg>${points.map(p=>`<div class="cycle-person" data-point="${p.m}">${avatar(p.m)}<strong>${esc(name(p.m))}</strong><small>${esc(place(c.edges.find(e=>e.giver===p.m).destination).name)}</small></div>`).join('')}<span class="cycle-center">full circle</span></div>`;
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
  return `<div class="side-card"><h3>Your pocket <span aria-hidden="true">↘</span></h3>${ownTrip?`<div class="pocket-row">${placeIcon(ownTrip.destination)}<div><div class="overline">You’re heading to</div><strong>${esc(place(ownTrip.destination).name)}</strong><small>${time(ownTrip.depart)} – ${time(ownTrip.returns)}</small><small>${ownTrip.capacity} small item spaces</small></div></div><button class="subtle-link" data-action="post" data-id="${ownTrip.id}">View your trip</button>`:`<p class="card-note">No trip posted yet.</p><button class="button small" data-action="add-trip">${icon('plus',14)}Add your trip</button>`}<div class="pocket-divider"></div>${ownNeed?`<div class="pocket-row">${icon('bag',21)}<div><div class="overline">You need a hand with</div><strong>${esc(ownNeed.item)}</strong><small>By ${time(ownNeed.deadline)}</small></div></div><button class="subtle-link" data-action="post" data-id="${ownNeed.id}">View your request</button>`:`<p class="card-note">Anything you need picked up?</p><button class="button small" data-action="add-request">${icon('plus',14)}Add a request</button>`}</div>`;
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
  dialogState={kind,id};
  $('#modal-content').innerHTML=`<div class="modal-head"><div><div class="eyebrow">${eyebrow}</div><h2 id="dialog-title">${title}</h2></div><button class="close" data-action="close" aria-label="Close dialog">×</button></div><div class="modal-body">${body}</div>`;
  if(!modal.open)modal.showModal();
  else if(focus)$('#modal-content button')?.focus();
}
function closeModal(){dialogState=null;modal.close();if(lastFocus?.isConnected)lastFocus.focus();}
function edgesHTML(c, progress=false){return c.edges.map(e=>`<div class="exchange-edge"><div class="edge-people">${avatar(e.giver)}<strong>${esc(name(e.giver))}</strong><span class="edge-arrow">collects for →</span>${avatar(e.receiver)}<strong>${esc(name(e.receiver))}</strong></div><h3>${esc(e.item)}</h3><p>${esc(place(e.destination).name)} · Return by ${time(e.returns)} · Needed by ${time(e.deadline)}</p>${progress?`<div class="edge-status">${e.received?`${icon('check',14)} Received and confirmed`:e.collected?'Collected · waiting for receiver confirmation':'Awaiting collection'}</div>${['active','needs_handoff'].includes(c.status)?`<div class="actions">${e.giver===actor&&!e.collected?`<button class="button small" data-mutation data-action="collected" data-id="${c.id}" data-request="${e.request}">I’ve collected this</button>`:''}${e.receiver===actor&&e.collected&&!e.received?`<button class="button small primary" data-mutation data-action="received" data-id="${c.id}" data-request="${e.request}">I’ve received this</button>`:''}</div>`:''}`:''}</div>`).join('');}
function showMatch(id){
  const c=state.matching.candidates.find(c=>c.id===id);if(!c){notify('This suggestion changed. Please refresh the board.');return;}
  openModal('A little help, all the way round.',`${c.members.length} neighbours · One exchange`,
    `<p>Here’s exactly who collects what. Nothing is agreed until every neighbour accepts.</p>${edgesHTML(c)}<div class="check-list"><span>${icon('check',15)}Same planned stops</span><span>${icon('check',15)}Deadlines fit</span><span>${icon('check',15)}Bag space checked</span></div><div class="callout guide-sub">All handovers are at the courtyard. Pickups must be prepared and paid for, with collection permission arranged separately.</div><div class="actions"><button class="button primary full" data-mutation data-action="propose" data-id="${id}">I’m in — propose this circle ${icon('arrow')}</button></div><p class="guide-sub">This reserves everyone’s posts while they decide. Unaccepted circles expire at the first departure.</p>`, 'match',id);
}
function showLoop(id,focus=true){
  const l=state.loops.find(l=>l.id===id);if(!l){closeModal();return;}
  const next=l.members.find(m=>!l.accepted.includes(m));
  openModal('Your circle, one step at a time.',statusNames[l.status],
    `${l.status==='needs_handoff'?'<div class="callout warning">Someone reported a problem after collection. Items already collected must still be handed over. Contact your group; these posts will not be rematched automatically.</div>':''}
    <div class="acceptance">${l.members.map(m=>`<span class="${l.accepted.includes(m)?'yes':''}">${l.accepted.includes(m)?'✓':'○'} ${esc(name(m))}</span>`).join('')}</div>${edgesHTML(l,true)}
    ${l.status==='awaiting'?`<div class="actions">${!l.accepted.includes(actor)?`<button class="button primary" data-mutation data-action="accept" data-id="${id}">Yes, I’m in ${icon('check')}</button><button class="button" data-mutation data-action="decline" data-id="${id}">Decline</button>`:'<p class="guide-sub">You’ve accepted. Waiting for the others.</p>'}</div><p class="guide-sub">Everyone must accept before ${time(l.expires)}.</p>`:''}
    ${['awaiting','active'].includes(l.status)?`<button class="subtle-link" data-action="cancel-loop-prompt" data-id="${id}">I can’t make this trip</button>`:''}
    ${l.status==='completed'?'<div class="callout">Every receiver confirmed their item. This circle is complete. Thanks for helping it happen.</div>':''}
    <div class="pocket-divider"></div><div class="guide-sub"><strong>Demo controls</strong> · Play another participant to test their consent and handover.<div class="actions">${l.members.filter(m=>m!==actor).map(m=>`<button class="button small" data-action="switch" data-member="${m}" data-loop="${id}">Continue as ${esc(member(m).name)}</button>`).join('')}</div></div>`, 'loop',id,focus);
}
function showPost(id){
  const p=[...state.trips,...state.requests].find(p=>p.id===id);if(!p)return;
  const trip='depart' in p;
  openModal(trip?esc(place(p.destination).name):esc(p.item),`${esc(name(p.member))} · ${trip?'Planned trip':'Pickup request'}`,
    `<p>${esc(p.note)}</p><div class="callout">${trip?`Leaves at ${time(p.depart)} · Returns by ${time(p.returns)}<br>Room for ${p.capacity} small items.`:`Ready at ${time(p.ready)} · Needed by ${time(p.deadline)}<br>${p.units} small-item space${p.units>1?'s':''} · ${esc(place(p.destination).name)}`}</div><p class="guide-sub">Status: ${esc(p.status)}. A small-item space is a rough carrying estimate agreed by this demo group.</p>${p.member===actor&&p.status==='open'?`<div class="actions"><button class="button danger" data-mutation data-action="cancel-post" data-id="${p.id}">Remove this ${trip?'trip':'request'}</button></div>`:''}${p.status==='reserved'||p.status==='active'?'<p class="guide-sub">This post is in a circle. Open My circles to manage it.</p>':''}`, 'post',id);
}
function localDate(ts){const d=new Date(ts*1000);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}T${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;}
function showForm(type){
  const existing=state[type==='trip'?'trips':'requests'].find(p=>p.member===actor&&['open','reserved','active'].includes(p.status));
  if(existing){showPost(existing.id);notify(`You already have a ${type}. Remove or finish it before adding another.`);return;}
  const now=Math.floor(Date.now()/1000), places=state.places.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  openModal(type==='trip'?'Where are you heading?':'What can someone pick up?',`${esc(name(actor))} · A small favour`,
    `<form id="post-form" data-type="${type}"><div class="form-error" id="form-error" role="alert" tabindex="-1"></div><div class="form-grid"><label class="field full">${type==='trip'?'I’m already going to':'Pickup location'}<select name="destination" required>${places}</select></label>
    ${type==='request'?'<label class="field full">What needs collecting?<input name="item" required maxlength="90" placeholder="e.g. My prepaid assignment printout"><small>Prepared collections only. Arrange payment and pickup permission separately.</small></label>':''}
    ${type==='trip'?`<label class="field">Leaving at<input type="datetime-local" name="depart" required value="${localDate(now+1800)}" min="${localDate(now+60)}" max="${localDate(now+86400)}"></label><label class="field">Back at courtyard by<input type="datetime-local" name="returns" required value="${localDate(now+3600)}" min="${localDate(now+120)}" max="${localDate(now+86400)}"></label>`:`<label class="field">Ready for pickup at<input type="datetime-local" name="ready" required value="${localDate(now)}"></label><label class="field">I need it by<input type="datetime-local" name="deadline" required value="${localDate(now+7200)}" min="${localDate(now+60)}" max="${localDate(now+86400)}"></label>`}
    <label class="field full">${type==='trip'?'Space I can offer':'Space this needs'}<select name="${type==='trip'?'capacity':'units'}">${[1,2,3,4,5].map(n=>`<option value="${n}">${n} small item${n>1?'s':''}</option>`).join('')}</select><small>Think a paperback, document envelope, or small prepared package per space.</small></label><label class="field full">A note for your neighbour<textarea name="note" maxlength="180" placeholder="Collection details, item size, or anything useful."></textarea></label></div><div class="actions"><button class="button primary full" type="submit">Post ${type==='trip'?'my trip':'my request'} ${icon('arrow')}</button></div><p class="guide-sub">One active trip and one active request per person. Exact existing destinations only; no detours.</p></form>`, 'form',type);
}
function guide(){openModal('A favour comes full circle.','The 2-minute walkthrough',
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
  else if(action==='refresh')await refresh(true);
  else if(action==='go-board'){currentView='board';render();}
  else if(action==='add-trip')showForm('trip');
  else if(action==='add-request')showForm('request');
  else if(action==='match')showMatch(id);
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
    const report={app:'ErrandLoop',exportedAt:new Date().toISOString(),notice:'Fictional campus demo. Not verified real-world impact.',loops:state.loops,activity:state.activity,metrics:state.metrics};
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='errandloop-activity.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
});
document.addEventListener('change',async event=>{
  if(event.target.id==='actor'){actor=event.target.value;localStorage.setItem('errandloop-actor',actor);closeModal();await refresh(true);}
  if(event.target.id==='place-filter'){destination=event.target.value;render();}
});
document.addEventListener('submit',async event=>{
  if(event.target.id!=='post-form')return;
  event.preventDefault();const form=event.target, type=form.dataset.type, data=Object.fromEntries(new FormData(form));
  for(const key of ['depart','returns','ready','deadline'])if(data[key])data[key]=Math.floor(new Date(data[key]).getTime()/1000);
  for(const key of ['units','capacity'])if(data[key])data[key]=Number(data[key]);
  await act(type,data,{message:'Posted. We’re looking for a circle that fits.'});
});
modal.addEventListener('cancel',()=>{dialogState=null;});
modal.addEventListener('click',e=>{if(e.target===modal){const r=modal.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeModal();}});
// The mutation observer only assigns diagram classes after a render.
new MutationObserver(layoutCycle).observe($('#app'),{childList:true,subtree:true});
await refresh(true);
setInterval(()=>{if(!document.hidden&&!saving)refresh();},15000);
