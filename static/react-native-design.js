(() => {
  const toggle = document.querySelector('#picture-text-toggle, #family-text-toggle');
  if (!toggle) return;
  const apply = enabled => {
    document.body.classList.toggle('rn-large-text', enabled);
    toggle.textContent = enabled ? 'A' : 'A+';
    localStorage.setItem('briga-rn-large-text', enabled ? '1' : '0');
  };
  apply(localStorage.getItem('briga-rn-large-text') === '1');
  toggle.addEventListener('click', () => apply(!document.body.classList.contains('rn-large-text')));
})();
