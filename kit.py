"""kit.py — design-system primitives for the v2 theme.

Every class emitted here is styled by theme.py. Do not add styling here;
add CSS there. This file is markup + a small JS bridge.

Layout contract (theme.py styles exactly these):
    with strip():                       # container key "strip": horizontal snap strip
        with panel("bill", "Bill", "March 2026", hint="...", size="l"):
            ...                         # container key "panel-l-bill"
Sizes: s (~26rem) · m (~40rem) · l (~58rem) · xl (full width)
"""
from contextlib import contextmanager
from html import escape as esc

import streamlit as st

# ---------------------------------------------------------------------------
# Icons: name -> inner SVG (24x24 viewBox, stroke = currentColor)
# ---------------------------------------------------------------------------
ICONS = {
    "bolt":    '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "gauge":   '<path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/><path d="M13.4 10.6 19 5"/><path d="M22 12a10 10 0 1 1-20 0"/>',
    "home":    '<path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/>',
    "users":   '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c.7-3.6 3.2-5.5 6-5.5S14.3 16.4 15 20"/><circle cx="17" cy="8" r="2.6"/><path d="M15 14.6c2.3.3 4.5 2 5 5.4"/>',
    "meter":   '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 14h8"/><path d="M12 10v8"/>',
    "chart":   '<path d="M4 20V4"/><path d="M4 20h16"/><path d="m7 14 4-4 3 3 5-6"/>',
    "map":     '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15"/><path d="M15 6v15"/>',
    "shield":  '<path d="M12 2 4 5v7c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V5z"/>',
    "doc":     '<path d="M6 2h9l5 5v15H6z"/><path d="M15 2v5h5"/><path d="M9 13h6M9 17h6"/>',
    "down":    '<path d="M12 4v12"/><path d="m6 12 6 6 6-6"/><path d="M4 20h16"/>',
    "warn":    '<path d="M12 3 2 21h20z"/><path d="M12 9v6"/><circle cx="12" cy="18" r=".6"/>',
    "plug":    '<path d="M9 3v6M15 3v6"/><path d="M5 9h14v3a7 7 0 0 1-14 0z"/><path d="M12 19v3"/>',
    "wave":    '<path d="M2 12c2-4 4-4 6 0s4 4 6 0 4-4 6 0"/>',
    "receipt": '<path d="M4 3h16v18l-4-2-4 2-4-2-4 2z"/><path d="M8 8h8M8 12h8M8 16h4"/>',
    "logout":  '<path d="M10 4H5v16h5"/><path d="M14 8l4 4-4 4"/><path d="M8 12h10"/>',
    "card":    '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18M7 15h3"/>',
    "plus":    '<path d="M12 5v14M5 12h14"/>',
    "list":    '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r=".8"/><circle cx="4" cy="12" r=".8"/><circle cx="4" cy="18" r=".8"/>',
}


def icon(name: str, size: int = 18) -> str:
    path = ICONS.get(name, ICONS["bolt"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{path}</svg>')


# ---------------------------------------------------------------------------
# Toasts: pages call toast(); the next run calls show_toasts() (real st.toast)
# ---------------------------------------------------------------------------
_TOAST_ICON = {"success": ":material/check_circle:", "warning": ":material/warning:",
               "error": ":material/error:", "info": ":material/info:"}


def toast(msg: str, kind: str = "success") -> None:
    st.session_state.setdefault("_toasts", []).append((kind, msg))


def show_toasts() -> None:
    for kind, msg in st.session_state.pop("_toasts", []):
        st.toast(msg, icon=_TOAST_ICON.get(kind, _TOAST_ICON["info"]))


# ---------------------------------------------------------------------------
# Strip + panel
# ---------------------------------------------------------------------------
@contextmanager
def strip():
    """Horizontal snap-scroll strip. Put `with panel(...)` blocks inside."""
    with st.container(key="strip"):
        yield
    controls()


@contextmanager
def panel(key: str, title: str | None = None, subtitle: str = "",
          hint: str | None = None, size: str = "m"):
    with st.container(key=f"panel-{size}-{key}"):
        if title:
            hint_html = (f'<span class="hint" tabindex="0" role="button" aria-label="Help">?'
                         f'<span class="hint-b">{esc(hint)}</span></span>') if hint else ""
            st.html(f'<div class="pn-h"><div><div class="pn-t">{esc(title)}</div>'
                    f'<div class="pn-s">{esc(subtitle)}</div></div>{hint_html}</div>')
        yield


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------
def stat(label, value, unit="", foot="", hero=False, alert=False):
    cls = "stat" + (" hero" if hero else "") + (" alert" if alert else "")
    u = f'<span class="stat-u">{esc(unit)}</span>' if unit else ""
    f = f'<div class="stat-f">{esc(foot)}</div>' if foot else ""
    st.html(f'<div class="{cls}"><div class="stat-l">{esc(label)}</div>'
            f'<div class="stat-v num">{esc(str(value))}{u}</div>{f}</div>')


def pill(text, kind="teal", live=False):
    """Returns HTML. kind: teal | amber | orange | gray."""
    cls = f"pill {kind}" + (" live" if live else "")
    return f'<span class="{cls}"><i></i>{esc(str(text))}</span>'


def show(html: str):
    """Render a small HTML fragment (e.g. a pill) on its own line."""
    st.html(f'<div class="inline">{html}</div>')


def delta(text, kind="flat"):
    """kind: up | down | flat. Returns HTML."""
    return f'<span class="delta {kind}">{esc(str(text))}</span>'


def banner(text, level="warn"):
    """level: warn (orange) | info (teal)."""
    lv = level if level in ("warn", "info") else "warn"
    st.html(
        f'<div class="banner {lv}"><span class="dot"></span>{esc(text)}</div>')


def kv(pairs):
    rows = "".join(f'<div><span>{esc(str(k))}</span><b>{esc(str(v))}</b></div>'
                   for k, v in pairs)
    st.html(f'<div class="kv">{rows}</div>')


def receipt(title, rows, total_label, total_value, ok=False):
    body = "".join(f'<div class="rcpt-r"><span>{esc(str(k))}</span><span>{esc(str(v))}</span></div>'
                   for k, v in rows)
    cls = "ok" if ok else ""
    st.html(f'<div class="rcpt"><div class="rcpt-h">{esc(title)}</div>{body}'
            f'<div class="rcpt-t"><span>{esc(total_label)}</span>'
            f'<b class="{cls}">{esc(str(total_value))}</b></div></div>')


def feed(items):
    """items: list of (title, subtitle[, kind]) where kind is '' | 'warn'."""
    out = ""
    for it in items:
        t, s = it[0], it[1]
        k = it[2] if len(it) > 2 else ""
        out += (f'<div class="feed-i {esc(k)}"><span class="feed-d"></span>'
                f'<div><div class="feed-t">{esc(str(t))}</div>'
                f'<div class="feed-s">{esc(str(s))}</div></div></div>')
    st.html(f'<div class="feed">{out}</div>')


def empty(icon_name, title, sub):
    st.html(f'<div class="empty"><span class="chip">{icon(icon_name, 24)}</span>'
            f'<b>{esc(title)}</b><span>{esc(sub)}</span></div>')


def row(primary, metric, cost):
    st.html(f'<div class="row-i"><span class="a">{esc(str(primary))}</span>'
            f'<span class="b">{esc(str(metric))}</span>'
            f'<span class="c">{esc(str(cost))}</span></div>')


def range_bar(q1, med, q3, lo, hi):
    span = max(hi - lo, 1)
    left = (q1 - lo) / span * 100
    width = (q3 - q1) / span * 100
    median = (med - lo) / span * 100
    st.html(f'<div class="range"><div class="iqr" style="left:{left:.1f}%;width:{width:.1f}%"></div>'
            f'<div class="med" style="left:{median:.1f}%"></div></div>'
            f'<div class="range-l"><span>{lo:,.0f}</span><span>{hi:,.0f}</span></div>')


def sparkline(values, width=280, height=64):
    values = [float(v) for v in values]
    if not values:
        return
    if len(values) == 1:
        values = values * 2
    lo, hi = min(values), max(values)
    pad = 4
    step = (width - 2 * pad) / max(len(values) - 1, 1)
    rng = (hi - lo) or 1
    pts = [(pad + i * step, height - pad - (v - lo) / rng * (height - 2 * pad))
           for i, v in enumerate(values)]
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    length = sum(((pts[i][0] - pts[i-1][0]) ** 2 + (pts[i][1] - pts[i-1][1]) ** 2) ** .5
                 for i in range(1, len(pts)))
    lx, ly = pts[-1]
    st.html(f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
            f'<path class="ln" d="{d}" style="--L:{length:.0f}"/>'
            f'<path class="dot" d="M{lx:.1f} {ly:.1f}h0"/></svg>')


# ---------------------------------------------------------------------------
# JS bridge: progress rail, active panel, per-page horizontal position restore,
# and arrow keys. Vertical wheel input is left to normal page scrolling.
# Idempotent: re-checks every 400 ms, so it also works when you navigate to a
# strip page later. Cleans up after itself when the iframe is unloaded.
# ---------------------------------------------------------------------------
_JS = r"""
<script>
(function(){
  const P = window.parent, D = P.document;
  const KEY = 'gm-scroll:' + P.location.pathname;
  let sig = '';

  const topChild = (strip, p) => { let el = p; while (el && el.parentElement !== strip) el = el.parentElement; return el; };

  function wire(){
    const strip = D.querySelector('.st-key-strip');
    const old = D.getElementById('gm-rail');
    if (!strip){
      if (old) old.remove();
      D.documentElement.classList.remove('has-strip', 'gm-ready');
      sig = ''; return;
    }
    D.documentElement.classList.add('has-strip');
    const panels = [...strip.querySelectorAll('[class*="st-key-panel-"]')];
    if (!panels.length) return;

    if (!strip.dataset.gmVerticalScroll){
      strip.dataset.gmVerticalScroll = '1';
      strip.addEventListener('wheel', e => {
        if (!e.ctrlKey && Math.abs(e.deltaY) > Math.abs(e.deltaX)) e.stopPropagation();
      }, true);
    }
    if (!strip.dataset.gmScroll){
      strip.dataset.gmScroll = '1';
      strip.addEventListener('scroll', () => {
        try { P.sessionStorage.setItem(KEY, String(strip.scrollLeft)); } catch(_){}
        paint();
      }, {passive:true});
      const saved = Number((function(){ try { return P.sessionStorage.getItem(KEY); } catch(_){ return 0; } })() || 0);
      if (saved) setTimeout(() => { strip.scrollLeft = saved; }, 60);
    }

    const labels = panels.map(p => {
      const t = p.querySelector('.pn-t');
      return ((t ? t.textContent : '') || p.className.replace(/.*st-key-panel-\w+-([\w-]+).*/, '$1')).slice(0, 18);
    });
    const nsig = labels.join('|');
    let rail = old;
    if (!rail || nsig !== sig){
      sig = nsig;
      if (rail) rail.remove();
      rail = D.createElement('div'); rail.id = 'gm-rail';
      rail.innerHTML = '<button class="gm-arrow" data-dir="-1" aria-label="Previous">‹</button>'
                     + '<div class="gm-dots"></div>'
                     + '<button class="gm-arrow" data-dir="1" aria-label="Next">›</button>';
      D.body.appendChild(rail);
      const dots = rail.querySelector('.gm-dots');
      panels.forEach((p, i) => {
        const b = D.createElement('button'); b.className = 'gm-dot';
        const ic = D.createElement('i'); const sp = D.createElement('span'); sp.textContent = labels[i];
        b.appendChild(ic); b.appendChild(sp);
        b.onclick = () => go(i);
        dots.appendChild(b);
      });
      rail.querySelectorAll('.gm-arrow').forEach(a => {
        a.onclick = () => {
          const dir = Number(a.dataset.dir), k = current();
          const j = Math.max(0, Math.min(panels.length - 1, k + dir));
          if (j === k) return;
          const wj = (topChild(strip, panels[dir > 0 ? k : j]) || panels[k]).getBoundingClientRect().width + 16;
          strip.scrollBy({left: dir * wj, behavior:'smooth'});
        };
      });
    }
    function current(){
      const base = strip.getBoundingClientRect().left;
      if (strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 4 && strip.scrollLeft > 0) return panels.length - 1;
      let best = 0, bd = 1e9;
      panels.forEach((p, i) => {
        const w = topChild(strip, p) || p;
        const d = Math.abs((w.getBoundingClientRect().left - base) );
        if (d < bd){ bd = d; best = i; }
      });
      return best;
    }
    function go(i){
      const w = topChild(strip, panels[i]) || panels[i];
      strip.scrollTo({left: strip.scrollLeft + w.getBoundingClientRect().left - strip.getBoundingClientRect().left - 2, behavior:'smooth'});
    }
    function paint(){
      const k = current();
      panels.forEach((p, i) => {
        const on = i === k; p.classList.toggle('gm-on', on);
        const w = topChild(strip, p); if (w && w !== p) w.classList.toggle('gm-on', on);
      });
      const r = D.getElementById('gm-rail');
      if (r) r.querySelectorAll('.gm-dot').forEach((d, i) => d.classList.toggle('on', i === k));
    }
    window.__gmPaint = paint; paint();
    D.documentElement.classList.add('gm-ready');
  }

  if (D.__gmKey) D.removeEventListener('keydown', D.__gmKey);
  D.__gmKey = e => {
    const t = e.target, tag = (t.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || t.isContentEditable) return;
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const r = D.getElementById('gm-rail'); if (!r) return;
    r.querySelector('.gm-arrow[data-dir="' + (e.key === 'ArrowRight' ? 1 : -1) + '"]').click();
  };
  D.addEventListener('keydown', D.__gmKey);

  wire();
  const timer = setInterval(wire, 400);
  const bye = () => { clearInterval(timer); const r = D.getElementById('gm-rail'); if (r) r.remove();
                      D.documentElement.classList.remove('has-strip', 'gm-ready'); };
  window.addEventListener('pagehide', bye);
  window.addEventListener('unload', bye);
})();
</script>
"""


def controls():
    st.iframe(_JS, height=1, width=1)
