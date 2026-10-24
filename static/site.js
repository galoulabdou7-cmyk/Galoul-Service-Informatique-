function toggleLanguage() {
  const current = localStorage.getItem('galoul-lang') || 'ar';
  const next = current === 'ar' ? 'en' : 'ar';
  localStorage.setItem('galoul-lang', next);
  applyLanguage(next);
}
function applyLanguage(lang) {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.body.classList.toggle('english', lang === 'en');
  document.querySelectorAll('[data-ar][data-en]').forEach(el => {
    const value = el.getAttribute('data-' + lang);
    if (value !== null) el.innerHTML = value;
  });
}
document.addEventListener('DOMContentLoaded', () => {
  applyLanguage(localStorage.getItem('galoul-lang') || 'ar');
});
