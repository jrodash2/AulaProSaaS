(() => {
  const normalize = value => (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const search = document.querySelector('[data-manual-search]');
  if (search) search.addEventListener('input', () => {
    const query = normalize(search.value);
    const items = [...document.querySelectorAll('[data-search-item]')];
    items.forEach(item => { item.hidden = query && !normalize(item.dataset.search + ' ' + item.textContent).includes(query); });
    const empty = document.querySelector('.manual-empty');
    if (empty) empty.hidden = items.some(item => !item.hidden);
  });
  document.querySelector('[data-index-toggle]')?.addEventListener('click', () => {
    const index = document.getElementById('manualIndex');
    const open = index.classList.toggle('is-open');
    document.body.classList.toggle('manual-index-open', open);
  });
  document.querySelectorAll('[data-copy-link]').forEach(button => button.addEventListener('click', async () => {
    const url = new URL(window.location.href); url.hash = button.dataset.copyLink;
    try { await navigator.clipboard.writeText(url.toString()); button.textContent = 'Enlace copiado'; }
    catch (_) { window.prompt('Copia este enlace:', url.toString()); }
  }));
  const progress = document.querySelector('.reading-progress span');
  if (progress) {
    const update = () => {
      const max = document.documentElement.scrollHeight - innerHeight;
      progress.style.width = `${max > 0 ? Math.min(100, scrollY / max * 100) : 100}%`;
    };
    addEventListener('scroll', update, {passive: true}); update();
  }
})();
