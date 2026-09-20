let mode = 'create';
let submitting = false;
const form = document.querySelector('#account-form');
const error = document.querySelector('#login-error');
const button = document.querySelector('#account-submit');
function choose(next) {
  mode = next;
  document.querySelectorAll('[data-fields]').forEach(el => {
    el.hidden = !el.dataset.fields.split(' ').includes(mode);
    el.querySelectorAll('input,textarea').forEach(input => { input.disabled = el.hidden; input.required = !el.hidden; });
  });
  document.querySelectorAll('[data-mode]').forEach(el => {
    el.classList.toggle('active', el.dataset.mode === mode);
    el.setAttribute('aria-pressed', String(el.dataset.mode === mode));
  });
  form.elements.password.autocomplete = mode === 'login' ? 'current-password' : 'new-password';
  button.textContent = {create:'Create my group ↗', join:'Join this group ↗', login:'Sign in ↗'}[mode];
  error.textContent = '';
}
document.querySelectorAll('[data-mode]').forEach(el => el.addEventListener('click', () => choose(el.dataset.mode)));
const invitation = new URLSearchParams(window.location.hash.slice(1)).get('join');
if (invitation && /^[a-f0-9]{32}$/.test(invitation)) {
  choose('join');
  form.elements.group_code.value = invitation;
  window.history.replaceState(null, '', window.location.pathname);
} else choose(mode);
form.addEventListener('submit', async event => {
  event.preventDefault();
  if(submitting)return;
  submitting=true; button.disabled=true; button.setAttribute('aria-busy','true');
  document.querySelectorAll('[data-mode]').forEach(el=>el.disabled=true);
  error.textContent='';
  const data = Object.fromEntries(new FormData(form));
  if (mode === 'create') data.places = data.places.split('\n').map(s=>s.trim()).filter(Boolean);
  try {
    const response = await fetch({create:'/api/groups/create',join:'/api/groups/join',login:'/api/session'}[mode], {
      signal:AbortSignal.timeout(15000), method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Unable to continue. Please try again.');
    form.reset(); window.location.replace('/');
  } catch (e) { error.textContent = e.name === 'TimeoutError' ? 'The server took too long to respond. Try signing in first: your account may already have been created.' : e.message; error.focus(); } finally { submitting=false; button.disabled=false; button.removeAttribute('aria-busy'); document.querySelectorAll('[data-mode]').forEach(el=>el.disabled=false); }
});
