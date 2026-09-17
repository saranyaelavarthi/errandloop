const form = document.querySelector('#login-form');
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  const error = document.querySelector('#login-error');
  button.disabled = true;
  error.textContent = '';
  try {
    const response = await fetch('/api/session', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code: new FormData(form).get('code')})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Unable to enter. Please retry.');
    form.reset();
    window.location.replace('/');
  } catch (e) {
    error.textContent = e.message;
    button.disabled = false;
  }
});
