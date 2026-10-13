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

    // weather line icons (matches the approved preview), from Open-Meteo codes
    weatherKey(code, isDay) {
      const c = code ?? 0, night = isDay === false;
      if (c >= 95) return 'thunder';
      if ((c >= 71 && c <= 77) || c === 85 || c === 86) return 'snow';
      if (c === 65 || c === 82 || c === 67) return 'heavy';
      if ((c >= 61 && c <= 66) || c === 80 || c === 81) return 'rain';
      if (c >= 51 && c <= 57) return 'drizzle';
      if (c === 45 || c === 48) return 'fog';
      if (c === 3) return 'cloudy';
      if (c === 1 || c === 2) return night ? 'partly_night' : 'partly';
      return night ? 'clear_night' : 'clear';
    },
    WEATHER_LABELS: { 0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
      61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 80: 'Showers', 81: 'Showers', 82: 'Heavy showers', 95: 'Thunderstorm' },
    weatherIcon(code, isDay) {
      const gold = '#F2B01E', rainC = 'var(--accent)';
      const sun = (cx = 12, cy = 12, r = 4.2) => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${gold}"/>` + [0, 45, 90, 135, 180, 225, 270, 315].map(a => {
        const t = a * Math.PI / 180, p = d => [(cx + Math.cos(t) * (r + d)).toFixed(1), (cy + Math.sin(t) * (r + d)).toFixed(1)];
        const [x1, y1] = p(2.2), [x2, y2] = p(4.3);
        return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${gold}" stroke-width="1.8" stroke-linecap="round"/>`; }).join('');
      const moon = (x = 0, y = 0) => `<path transform="translate(${x} ${y})" d="M15.5 4.5a7.5 7.5 0 1 0 4 13.4A8.5 8.5 0 0 1 15.5 4.5z" fill="#9FB3D1"/>`;
      const cloud = (fill, dy = 0) => `<path transform="translate(0 ${dy})" d="M7 19h10.2a4.3 4.3 0 0 0 .5-8.6A6 6 0 0 0 6.3 11.6 3.8 3.8 0 0 0 7 19z" fill="${fill}"/>`;
      const drops = (n, len) => Array.from({ length: n }, (_, i) => { const x = 8 + i * (8 / Math.max(1, n - 1));
        return `<line x1="${x}" y1="20.5" x2="${x - 1.2}" y2="${20.5 + len}" stroke="${rainC}" stroke-width="1.8" stroke-linecap="round"/>`; }).join('');
      const ICONS = {
        clear: sun(), clear_night: moon(-2, 1),
        partly: sun(9, 8.5, 3.6) + cloud('#C9D4E3', 2), partly_night: moon(-4, -2) + cloud('#C9D4E3', 2),
        cloudy: cloud('#9AA9BD', -1),
        fog: cloud('#C9D4E3', -3) + '<path d="M5 19h14M7 22h10" stroke="#9AA9BD" stroke-width="1.8" stroke-linecap="round"/>',
        drizzle: cloud('#B7C4D6', -3) + [8, 12, 16].map(x => `<circle cx="${x}" cy="21" r="1" fill="${rainC}"/>`).join(''),
        rain: cloud('#A9B8CC', -3) + drops(3, 2.6), heavy: cloud('#8E9FB6', -3) + drops(4, 3.4),
        snow: cloud('#C9D4E3', -3) + [8, 12, 16].map(x => `<path d="M${x} 19.5v3.4M${x - 1.5} 20.4l3 1.6M${x + 1.5} 20.4l-3 1.6" stroke="#7FB2E5" stroke-width="1.2" stroke-linecap="round"/>`).join(''),
        thunder: cloud('#7F90A8', -3) + '<path d="M12.5 17l-2.5 4h2.6l-1.6 3.2 4.2-4.8h-2.6l1.6-2.4z" fill="#E0A100"/>',
      };
      const label = TC.WEATHER_LABELS[code] || '';
      return `<svg viewBox="0 0 24 26" role="img" aria-label="${label}">${ICONS[TC.weatherKey(code, isDay)]}</svg>`;
    },

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
