// Shared helpers for every page: theme toggle, CSRF, escaping, safe markdown,
// and Chart.js defaults that follow the current theme.
(function () {
  const THEMES = ['system', 'light', 'dark'];
  const LABELS = { system: 'Theme: auto', light: 'Theme: light', dark: 'Theme: dark' };
  const themeListeners = [];

  function storedTheme() {
    try { return localStorage.getItem('tc-theme') || 'system'; } catch (e) { return 'system'; }
  }

  function applyTheme(t) {
    if (t === 'system') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', t);
    document.querySelectorAll('[data-theme-label]').forEach(el => { el.textContent = LABELS[t]; });
    applyChartDefaults();
    themeListeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });
  }

  function cycleTheme() {
    const next = THEMES[(THEMES.indexOf(storedTheme()) + 1) % THEMES.length];
    try { localStorage.setItem('tc-theme', next); } catch (e) {}
    applyTheme(next);
  }

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function applyChartDefaults() {
    if (!window.Chart) return;
    Chart.defaults.font.family = css('--f-ui');
    Chart.defaults.font.size = 11;
    Chart.defaults.color = css('--muted');
    Chart.defaults.borderColor = css('--line');
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
    Chart.defaults.plugins.legend.labels.boxHeight = 10;
    Chart.defaults.plugins.tooltip.backgroundColor = css('--ink');
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
  }

  // React to OS theme changes while on "system"
  try {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (storedTheme() === 'system') applyTheme('system');
    });
  } catch (e) {}

  window.TC = {
    css,
    onTheme(fn) { themeListeners.push(fn); },

    getCookie(name) {
      const parts = `; ${document.cookie}`.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    },

    escapeHtml(s) {
      const d = document.createElement('div');
      d.textContent = s == null ? '' : String(s);
      return d.innerHTML;
    },

    // model output is untrusted: markdown -> HTML -> sanitized
    markdown(text) {
      const html = window.marked ? marked.parse(text || '') : TC.escapeHtml(text);
      return window.DOMPurify ? DOMPurify.sanitize(html) : TC.escapeHtml(text);
    },

    postJSON(url, body) {
      return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': TC.getCookie('csrftoken') },
        body: JSON.stringify(body),
      });
    },

    // activity type -> palette slot (matches TYPE_KEYS in coach/views.py)
    typeKey(t) {
      t = (t || '').toLowerCase();
      if (t.includes('cycl') || t.includes('bik')) return 'cycling';
      if (t.includes('run') || t.includes('treadmill')) return 'running';
      if (t.includes('skat')) return 'skating';
      if (t.includes('tennis')) return 'tennis';
      if (t.includes('plyo')) return 'plyometrics';
      if (t.includes('ski') || t.includes('hik') || t.includes('mountain') || t.includes('walk')) return 'outdoor';
      if (t.includes('strength') || t.includes('gym') || t.includes('weight')) return 'strength';
      return 'other';
    },
    TYPE_ORDER: ['cycling', 'running', 'skating', 'tennis', 'plyometrics', 'outdoor', 'strength', 'other'],
    TYPE_LABELS: { cycling: 'Cycling', running: 'Running', skating: 'Skating', tennis: 'Tennis',
      plyometrics: 'Plyometrics', outdoor: 'Ski & hike', strength: 'Strength', other: 'Other' },
    typeColor(t) { return TC.css('--t-' + TC.typeKey(t)); },

    label(t) { return (t || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); },

    // canvas can't parse color-mix(); turn a #RRGGBB token into rgba()
    alpha(hex, a) {
      const h = (hex || '').replace('#', '');
      if (h.length !== 6) return hex;
      const n = parseInt(h, 16);
      return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-theme-toggle]').forEach(b => b.addEventListener('click', cycleTheme));
    applyTheme(storedTheme());
  });
})();
