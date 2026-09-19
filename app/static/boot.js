// Independent of the main module: a failed script must not leave an endless spinner.
(() => {
  function recover() {
    const loading = document.querySelector('#app .loading');
    if (!loading) return;
    const panel = document.createElement('section');
    panel.className = 'empty';
    panel.setAttribute('role', 'alert');
    const title = document.createElement('h2');
    title.textContent = 'The board could not start.';
    const detail = document.createElement('p');
    detail.textContent = 'Keep the ErrandLoop terminal running. After updating, restart it and press Ctrl+Shift+R to reload this page. Your saved groups have not been deleted.';
    const retry = document.createElement('button');
    retry.className = 'button primary';
    retry.textContent = 'Reload the board';
    retry.addEventListener('click', () => window.location.reload());
    const help = document.createElement('p');
    help.className = 'guide-sub';
    help.textContent = 'Still stuck? Share the terminal error and the first red error from browser Developer Tools > Console.';
    panel.append(title, detail, retry, help);
    loading.replaceWith(panel);
  }
  window.addEventListener('error', recover);
  window.addEventListener('unhandledrejection', recover);
  setTimeout(recover, 18000);
})();
