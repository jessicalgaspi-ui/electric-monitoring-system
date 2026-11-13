"""Visual theme v2 — dark-glass control room over the dusk pole scene.

Styles exactly the classes/keys emitted by kit.py (strip, panel-*, stat, pill,
rcpt, feed, ...). Palette proportion: ~70% navy glass, ~20% teal/sky (data and
interaction), ~10% amber/orange (amber = current/energy, orange = needs attention).

Kept for old call sites: apply_theme(), page_header(), tip(), eyebrow(),
step_card_header(). New: style_chart().
"""

import base64
from functools import lru_cache
from html import escape as esc

import streamlit as st

from kit import icon

SKY = "#8ecae6"
TEAL = "#219ebc"
NAVY = "#023047"
AMBER = "#ffb703"
ORANGE = "#fb8500"


def _pole_scene_svg() -> str:
    stars = [(90, 60, 1.6), (240, 130, 1.2), (380, 40, 1.4), (520, 110, 1.1),
             (700, 55, 1.5), (860, 140, 1.2), (1010, 70, 1.6), (1150, 30, 1.2),
             (1290, 120, 1.5), (1420, 60, 1.3), (1540, 150, 1.1), (610, 190, 1.0),
             (1190, 200, 1.0), (60, 210, 1.1), (1480, 240, 1.0)]
    star_svg = "".join(
        f'<circle class="tw" style="animation-delay:{(i % 7) * .45}s" cx="{x}" cy="{y}" r="{r}" fill="#ffffff" opacity="0.55"/>'
        for i, (x, y, r) in enumerate(stars))

    pole_x = [-320, 120, 560, 1000, 1440, 1880]
    arm_top, arm_low = 300, 385
    attach = [(arm_top, -75), (arm_top, 0), (arm_top, 75),
              (arm_low, -48), (arm_low, 48)]

    wires = []
    for y, dx in attach:
        for a, b in zip(pole_x, pole_x[1:]):
            x1, x2 = a + dx, b + dx
            wires.append(
                f'<path d="M{x1} {y} Q{(x1 + x2) / 2} {y + 46} {x2} {y}" '
                f'fill="none" stroke="#8ecae6" stroke-opacity="0.45" stroke-width="2"/>')

    flow = []
    for y, dx, delay in [(arm_top, 0, 0), (arm_low, -48, .9), (arm_top, 75, 1.5)]:
        for a, b in zip(pole_x, pole_x[1:]):
            x1, x2 = a + dx, b + dx
            flow.append(
                f'<path class="flow" style="animation-delay:{delay}s" '
                f'd="M{x1} {y} Q{(x1 + x2) / 2} {y + 46} {x2} {y}" fill="none" '
                f'stroke="#ffb703" stroke-width="3" stroke-linecap="round"/>')
    svg_css = ('<style>.tw{animation:tw 3.2s ease-in-out infinite}'
               '@keyframes tw{0%,100%{opacity:.15}50%{opacity:.95}}'
               '.ins{animation:ins 2.4s ease-in-out infinite}'
               '@keyframes ins{0%,100%{opacity:.5}50%{opacity:1}}'
               '.flow{stroke-dasharray:10 88;animation:flow 2.2s linear infinite}'
               '@keyframes flow{to{stroke-dashoffset:-98}}'
               '.bolt{animation:bolt 8s infinite}'
               '@keyframes bolt{0%,86%,100%{opacity:.04}88%{opacity:.5}90%{opacity:.08}92%{opacity:.45}}'
               '</style>')

    poles = []
    for x in pole_x[1:-1]:
        poles.append(f'''
<g fill="#01141f">
  <rect x="{x - 8}" y="270" width="16" height="640" rx="3"/>
  <rect x="{x - 90}" y="{arm_top - 6}" width="180" height="12" rx="3"/>
  <rect x="{x - 60}" y="{arm_low - 6}" width="120" height="10" rx="3"/>
  <path d="M{x - 8} {arm_top + 40} L{x - 70} {arm_top + 6} L{x - 66} {arm_top} L{x - 8} {arm_top + 30}Z"/>
  <path d="M{x + 8} {arm_top + 40} L{x + 70} {arm_top + 6} L{x + 66} {arm_top} L{x + 8} {arm_top + 30}Z"/>
</g>
<g class="ins" fill="#ffb703">
  <circle cx="{x - 75}" cy="{arm_top - 9}" r="4"/><circle cx="{x}" cy="{arm_top - 14}" r="4"/>
  <circle cx="{x + 75}" cy="{arm_top - 9}" r="4"/>
  <circle cx="{x - 48}" cy="{arm_low - 8}" r="3.5"/><circle cx="{x + 48}" cy="{arm_low - 8}" r="3.5"/>
</g>
<g fill="#ffb703" opacity="0.18">
  <circle cx="{x}" cy="{arm_top - 14}" r="16"/>
</g>''')
    tx = pole_x[2]
    transformer = (f'<g fill="#01141f"><rect x="{tx + 12}" y="430" width="34" height="52" rx="6"/>'
                   f'<rect x="{tx + 20}" y="422" width="18" height="10" rx="2"/></g>')

    bolt = ('<path d="M1330 70 L1290 150 L1322 150 L1296 225 L1372 128 L1336 128 L1362 70Z" '
            'class="bolt" fill="#ffb703" opacity="0.3" transform="translate(-700 470) scale(1.1)"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMax slice">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#01202f"/><stop offset="0.45" stop-color="#023047"/>
<stop offset="0.78" stop-color="#0f6786"/><stop offset="0.93" stop-color="#219ebc"/>
<stop offset="1" stop-color="#8ecae6"/></linearGradient>
<radialGradient id="glow" cx="0.5" cy="1" r="0.55">
<stop offset="0" stop-color="#ffb703" stop-opacity="0.55"/>
<stop offset="0.5" stop-color="#fb8500" stop-opacity="0.18"/>
<stop offset="1" stop-color="#fb8500" stop-opacity="0"/></radialGradient>
</defs>
{svg_css}
<rect width="1600" height="900" fill="url(#sky)"/>
<rect width="1600" height="900" fill="url(#glow)"/>
{star_svg}
{bolt}
<path d="M0 760 Q220 690 460 745 T900 735 T1360 750 T1600 715 L1600 900 L0 900Z" fill="#01293c" opacity="0.85"/>
<path d="M0 820 Q300 770 620 815 T1200 810 T1600 790 L1600 900 L0 900Z" fill="#011c2a"/>
{''.join(wires)}
{''.join(flow)}
{''.join(poles)}
{transformer}
</svg>'''



_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap');

:root{
  --navy:#023047; --teal:#219ebc; --sky:#8ecae6; --amber:#ffb703; --orange:#fb8500;
  --ink:#e8f4fa; --mut:rgba(232,244,250,.62); --faint:rgba(232,244,250,.38);
  --glass:rgba(2,26,40,.76); --glass-hi:rgba(3,40,60,.90); --line:rgba(142,202,230,.20);
  --disp:'Space Grotesk','Segoe UI',system-ui,sans-serif;
  --body:'Inter','Segoe UI',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,Consolas,monospace;
  --strip-h:max(430px, calc(100vh - 13.2rem));
  --strip-h:max(430px, calc(100dvh - 13.2rem));
}

/* ---------- base ---------- */
.stApp{
  background:
    linear-gradient(rgba(1,20,31,.60), rgba(1,26,41,.46)),
    url("data:image/svg+xml;base64,__SCENE__") no-repeat center bottom / cover fixed;
  color:var(--ink); color-scheme:dark; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
[data-testid="stMarkdownContainer"], [data-baseweb]{ font-family:var(--body); }
.stApp h1,.stApp h2,.stApp h3{ font-family:var(--disp); letter-spacing:-.01em; color:#fff; }
.num, [data-testid="stMetricValue"], [data-testid="stMetricValue"] *{
  font-family:var(--mono) !important; font-variant-numeric:tabular-nums; }
#MainMenu, footer{ visibility:hidden; }
header[data-testid="stHeader"]{ background:var(--glass) !important; backdrop-filter:blur(12px);
  -webkit-backdrop-filter:blur(12px); border-bottom:1px solid var(--line); }
.block-container{ padding:4.2rem 1.4rem .5rem !important; max-width:100% !important; }
[data-testid="stHorizontalBlock"]{ gap:1rem; }
[data-testid="stVerticalBlock"]{ gap:.75rem; }
[data-testid="stElementContainer"]:has(iframe[height="1"]){
  position:absolute !important; width:0; height:0; overflow:hidden; margin:0 !important; }

/* ---------- glass ---------- */
[class*="st-key-panel-"], [class*="st-key-tile-"], [data-testid="stExpander"], div[role="dialog"]{
  background:var(--glass); border:1px solid var(--line); border-radius:20px;
  backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
  box-shadow:0 12px 34px rgba(1,14,22,.42); }
[data-testid="stVerticalBlockBorderWrapper"]{ border-color:var(--line) !important; border-radius:16px; }
[class*="st-key-panel-"] [data-testid="stVerticalBlockBorderWrapper"]{ background:rgba(255,255,255,.04); }

/* ---------- page header (compact) ---------- */
.ph{ display:flex; align-items:center; gap:14px; margin:0 0 .6rem; padding:8px 16px;
  background:var(--glass); border:1px solid var(--line); border-radius:18px;
  backdrop-filter:blur(12px); animation:slideIn .5s cubic-bezier(.2,.8,.2,1) backwards; }
.ph-icon{ width:42px; height:42px; border-radius:13px; display:grid; place-items:center; flex:none;
  color:#021b29; background:linear-gradient(135deg,var(--amber),var(--orange));
  box-shadow:0 0 22px rgba(255,183,3,.5); animation:glow 3s ease-in-out infinite; }
.ph h1{ margin:0; padding:0; font-size:1.45rem; font-weight:700; line-height:1.1; }
.ph p{ margin:2px 0 0; color:var(--mut); font-size:.86rem; }
.eyebrow{ display:inline-block; margin:2px 0 4px; font-size:.7rem; font-weight:600;
  letter-spacing:.16em; text-transform:uppercase; color:var(--amber); }
details.tip{ margin:0 0 .5rem; font-size:.85rem; color:var(--mut); }
details.tip summary{ cursor:pointer; list-style:none; display:inline-flex; align-items:center; gap:6px;
  padding:3px 12px; border-radius:999px; border:1px solid var(--line); background:rgba(255,255,255,.05);
  color:var(--sky); font-weight:600; font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; }
details.tip summary::-webkit-details-marker{ display:none; }
details.tip div{ padding:8px 4px 0; line-height:1.5; }
.inline{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; }

/* ---------- strip + panels ---------- */
div.st-key-strip{
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important; align-items:stretch !important;
  gap:1rem !important; min-height:var(--strip-h); height:auto; overflow-x:auto; overflow-y:hidden;
  scroll-snap-type:x proximity; padding:2px 2px 10px; overscroll-behavior-x:contain;
  scrollbar-width:thin; scrollbar-color:rgba(142,202,230,.45) transparent; }
div.st-key-strip::-webkit-scrollbar{ height:6px; }
div.st-key-strip::-webkit-scrollbar-thumb{ background:rgba(142,202,230,.45); border-radius:6px; }
div.st-key-strip > *{ flex:0 0 auto; min-height:var(--strip-h); height:auto; min-width:0; scroll-snap-align:start;
  opacity:.5; transform:scale(.985); transition:opacity .35s ease, transform .35s ease;
  animation:rise .6s cubic-bezier(.2,.8,.2,1) backwards; }
div.st-key-strip > *:nth-child(2){ animation-delay:.07s; } div.st-key-strip > *:nth-child(3){ animation-delay:.14s; }
div.st-key-strip > *:nth-child(4){ animation-delay:.21s; } div.st-key-strip > *:nth-child(5){ animation-delay:.28s; }
div.st-key-strip > *.gm-on, div.st-key-strip > *:only-child{ opacity:1; transform:none; }
html:not(.gm-ready) div.st-key-strip > *{ opacity:1; transform:none; }

[class*="st-key-panel-"]{ min-height:var(--strip-h); height:auto; overflow:visible; padding:1.1rem 1.3rem !important;
  scrollbar-width:thin; scrollbar-color:rgba(142,202,230,.35) transparent; }
div.st-key-strip > [class*="st-key-panel-s-"]{ flex-basis:min(26rem, 88vw); }
div.st-key-strip > [class*="st-key-panel-m-"]{ flex-basis:min(40rem, 90vw); }
div.st-key-strip > [class*="st-key-panel-l-"]{ flex-basis:min(58rem, 92vw); }
div.st-key-strip > [class*="st-key-panel-xl-"]{ flex-basis:calc(100% - 4px); }
/* if Streamlit wraps each panel in a layout wrapper, size the wrapper by the panel it holds */
div.st-key-strip > *:has([class*="st-key-panel-s-"]){ flex-basis:min(26rem, 88vw); }
div.st-key-strip > *:has([class*="st-key-panel-m-"]){ flex-basis:min(40rem, 90vw); }
div.st-key-strip > *:has([class*="st-key-panel-l-"]){ flex-basis:min(58rem, 92vw); }
div.st-key-strip > *:has([class*="st-key-panel-xl-"]){ flex-basis:calc(100% - 4px); }
div.st-key-strip > * > [class*="st-key-panel-"]{ width:100%; }
iframe[title="streamlit_folium.st_folium"]{ height:calc(var(--strip-h) - 7.5rem) !important; border-radius:14px; }
@media (max-width:820px){ .block-container{ padding:4rem .7rem .4rem !important; } }

/* panel header + hint */
.pn-h{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:.2rem; }
.pn-t{ font-family:var(--disp); font-size:1.25rem; font-weight:700; color:#fff; line-height:1.15; }
.pn-s{ color:var(--mut); font-size:.82rem; margin-top:2px; }
.st-key-panel-m-welcome .pn-t{ font-size:1.8rem; letter-spacing:-.035em; }
.hero-title{ font:700 1.55rem/1.2 var(--disp); letter-spacing:-.025em; color:#fff;
  margin:0 0 .65rem; }
.hero-description{ max-width:34rem; color:var(--mut); font:400 .96rem/1.75 var(--body); }
.hint{ position:relative; flex:none; width:24px; height:24px; border-radius:50%; display:grid; place-items:center;
  font-weight:700; font-size:.8rem; color:var(--sky); border:1px solid var(--line); cursor:help; outline:none;
  transition:background .2s,color .2s; }
.hint:hover, .hint:focus{ background:rgba(33,158,188,.3); color:#fff; }
.hint-b{ position:absolute; top:30px; right:0; width:min(260px,70vw); padding:10px 12px; z-index:50;
  background:var(--glass-hi); border:1px solid var(--line); border-radius:12px; color:var(--ink);
  font:500 .8rem/1.45 var(--body); text-align:left; box-shadow:0 12px 28px rgba(1,14,22,.5);
  opacity:0; transform:translateY(-4px); pointer-events:none; transition:opacity .2s, transform .2s; }
.hint:hover .hint-b, .hint:focus .hint-b, .hint:focus-within .hint-b{ opacity:1; transform:none; }

/* progress rail */
#gm-rail{ position:fixed; left:50%; bottom:10px; transform:translateX(-50%); z-index:999;
  display:flex; align-items:center; gap:4px; padding:5px 8px; border-radius:999px; max-width:96vw;
  background:var(--glass-hi); border:1px solid var(--line); backdrop-filter:blur(12px); animation:rise .5s backwards; }
.gm-dots{ display:flex; gap:2px; overflow-x:auto; scrollbar-width:none; }
.gm-arrow, .gm-dot{ all:unset; cursor:pointer; box-sizing:border-box; color:var(--mut); font:600 .7rem var(--body);
  letter-spacing:.09em; text-transform:uppercase; border-radius:999px; transition:background .2s,color .2s,transform .2s; }
.gm-arrow{ padding:1px 10px; font-size:1.1rem; }
.gm-dot{ display:inline-flex; align-items:center; gap:7px; padding:4px 11px; white-space:nowrap; }
.gm-dot i{ width:6px; height:6px; border-radius:50%; background:currentColor; opacity:.5; transition:all .25s; }
.gm-arrow:hover, .gm-dot:hover{ color:#fff; background:rgba(33,158,188,.3); }
.gm-dot.on{ color:#021b29; background:linear-gradient(135deg,var(--amber),var(--orange)); }
.gm-dot.on i{ opacity:1; box-shadow:0 0 8px #fff; }
@media (max-width:640px){ .gm-dot span{ display:none; } .gm-dot.on span{ display:inline; } }

/* ---------- stat / hero ---------- */
.stat{ padding:.1rem 0 .3rem; }
.stat-l{ font-size:.7rem; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--sky); }
.stat-v{ font-size:1.7rem; font-weight:700; color:#fff; line-height:1.15; margin-top:2px; }
.stat-u{ font-size:.85rem; font-weight:500; color:var(--mut); margin-left:6px; }
.stat-f{ color:var(--mut); font-size:.82rem; margin-top:2px; }
.stat.hero .stat-v{ font-size:clamp(2.6rem, 9vh, 5rem); line-height:1.02; text-shadow:0 0 28px rgba(255,183,3,.35); }
.stat.hero .stat-u{ font-size:1.1rem; }
.stat.alert .stat-v{ color:var(--orange); text-shadow:0 0 30px rgba(251,133,0,.55); }
[data-testid="stMetricLabel"] p{ color:var(--mut) !important; font-size:.7rem !important; font-weight:600;
  letter-spacing:.12em; text-transform:uppercase; }
[data-testid="stMetricValue"]{ color:#fff; font-weight:700; font-size:1.5rem; }
[data-testid="stCaptionContainer"]{ color:var(--mut); }
[data-testid="stMetric"]{ transition:transform .25s; }
[data-testid="stMetric"]:hover{ transform:translateX(4px); }
[data-testid="stMetric"]:hover [data-testid="stMetricValue"]{ color:var(--amber); }

/* ---------- pills, deltas, banner ---------- */
.pill{ display:inline-flex; align-items:center; gap:7px; padding:3px 11px; border-radius:999px; border:1px solid transparent;
  font:700 .68rem var(--body); letter-spacing:.1em; text-transform:uppercase; }
.pill i{ width:7px; height:7px; border-radius:50%; background:currentColor; }
.pill.live i{ animation:pulse 1.6s ease-in-out infinite; }
.pill.teal{ background:rgba(33,158,188,.2); color:var(--sky); border-color:rgba(142,202,230,.4); }
.pill.amber{ background:rgba(255,183,3,.14); color:var(--amber); border-color:rgba(255,183,3,.45); }
.pill.orange{ background:rgba(251,133,0,.18); color:#ffb35c; border-color:rgba(251,133,0,.55); }
.pill.gray{ background:rgba(255,255,255,.06); color:var(--mut); border-color:var(--line); }
.delta{ display:inline-block; padding:2px 9px; border-radius:999px; font:600 .72rem var(--mono); }
.delta.up{ background:rgba(251,133,0,.16); color:#ffb35c; } .delta.down{ background:rgba(33,158,188,.2); color:var(--sky); }
.delta.flat{ background:rgba(255,255,255,.07); color:var(--mut); }
.banner{ display:flex; align-items:center; gap:10px; padding:8px 14px; margin:0 0 .6rem; border-radius:14px;
  font-weight:600; font-size:.88rem; color:#fff; background:var(--glass); border:1px solid rgba(251,133,0,.5); }
.banner.info{ border-color:rgba(142,202,230,.4); }
.banner .dot{ width:9px; height:9px; border-radius:50%; background:var(--orange); animation:pulse 1.4s ease-in-out infinite; flex:none; }
.banner.info .dot{ background:var(--teal); }

/* ---------- kv / receipt / feed / empty / row / range / spark ---------- */
.kv{ display:grid; gap:2px; }
.kv > div{ display:flex; justify-content:space-between; gap:12px; padding:7px 0; border-bottom:1px dashed var(--line); font-size:.88rem; }
.kv span{ color:var(--mut); } .kv b{ font-family:var(--mono); font-weight:600; color:#fff; text-align:right; }
.rcpt{ padding:16px 18px; border-radius:16px; background:rgba(255,255,255,.05); border:1px dashed rgba(142,202,230,.4);
  animation:rise .5s cubic-bezier(.2,.8,.2,1) backwards; }
.rcpt-h{ font:700 .72rem var(--body); letter-spacing:.16em; text-transform:uppercase; color:var(--amber); margin-bottom:8px; }
.rcpt-r{ display:flex; justify-content:space-between; padding:5px 0; font-size:.88rem; color:var(--mut); }
.rcpt-r span:last-child{ font-family:var(--mono); color:var(--ink); }
.rcpt-t{ display:flex; justify-content:space-between; align-items:baseline; margin-top:8px; padding-top:10px; border-top:1px solid var(--line); }
.rcpt-t span{ font:600 .75rem var(--body); letter-spacing:.12em; text-transform:uppercase; color:var(--sky); }
.rcpt-t b{ font:700 1.7rem var(--mono); color:#fff; } .rcpt-t b.ok{ color:var(--amber); text-shadow:0 0 20px rgba(255,183,3,.45); }
.feed{ display:grid; gap:2px; }
.feed-i{ display:flex; gap:12px; padding:9px 4px; border-bottom:1px solid rgba(142,202,230,.1); transition:background .2s, transform .2s; border-radius:10px; }
.feed-i:hover{ background:rgba(33,158,188,.12); transform:translateX(3px); }
.feed-d{ width:8px; height:8px; margin-top:6px; border-radius:50%; background:var(--teal); flex:none; box-shadow:0 0 8px var(--teal); }
.feed-i.warn .feed-d{ background:var(--orange); box-shadow:0 0 8px var(--orange); animation:pulse 1.6s ease-in-out infinite; }
.feed-t{ font-weight:600; font-size:.9rem; color:#fff; } .feed-s{ font-size:.8rem; color:var(--mut); margin-top:1px; }
.empty{ display:grid; justify-items:center; gap:6px; padding:28px 12px; text-align:center; color:var(--mut); }
.empty b{ color:#fff; font-family:var(--disp); font-size:1.05rem; }
.empty .chip{ width:52px; height:52px; border-radius:16px; display:grid; place-items:center; color:var(--sky);
  background:rgba(33,158,188,.15); box-shadow:0 0 24px rgba(33,158,188,.3); }
.row-i{ display:grid; grid-template-columns:1.1fr 1fr 1fr; gap:8px; padding:9px 8px; border-bottom:1px solid rgba(142,202,230,.1);
  font-size:.88rem; border-radius:10px; transition:background .2s; border-left:3px solid transparent; }
.row-i:hover{ background:rgba(33,158,188,.12); border-left-color:var(--amber); }
.row-i .a{ font-weight:600; color:#fff; } .row-i .b{ font-family:var(--mono); color:var(--sky); } .row-i .c{ font-family:var(--mono); color:var(--ink); text-align:right; }
.range{ position:relative; height:10px; border-radius:6px; background:rgba(255,255,255,.08); margin:10px 0 4px; }
.range .iqr{ position:absolute; top:0; bottom:0; border-radius:6px; background:linear-gradient(90deg,var(--teal),var(--sky)); }
.range .med{ position:absolute; top:-4px; bottom:-4px; width:3px; border-radius:2px; background:var(--amber); box-shadow:0 0 8px var(--amber); }
.range-l{ display:flex; justify-content:space-between; font:500 .72rem var(--mono); color:var(--faint); }
.spark{ width:100%; height:64px; overflow:visible; }
.spark .ln{ fill:none; stroke:var(--amber); stroke-width:2.4; vector-effect:non-scaling-stroke; stroke-linecap:round; stroke-linejoin:round;
  filter:drop-shadow(0 0 6px rgba(255,183,3,.6)); stroke-dasharray:var(--L); stroke-dashoffset:var(--L); animation:draw 1.4s ease forwards; }
.spark .dot{ fill:none; stroke:var(--amber); stroke-width:8; stroke-linecap:round; vector-effect:non-scaling-stroke;
  filter:drop-shadow(0 0 6px var(--amber)); animation:blink 1.8s ease-in-out infinite; }

/* ---------- widgets ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button{
  position:relative; overflow:hidden; border-radius:12px; font-weight:600; background:rgba(255,255,255,.06);
  color:var(--ink); border:1px solid rgba(142,202,230,.35);
  transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.stButton > button::after, .stDownloadButton > button::after, [data-testid="stFormSubmitButton"] > button::after{
  content:""; position:absolute; inset:0; transform:translateX(-120%); pointer-events:none;
  background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.26) 50%,transparent 70%); transition:transform .6s ease; }
.stButton > button:hover::after, .stDownloadButton > button:hover::after, [data-testid="stFormSubmitButton"] > button:hover::after{ transform:translateX(120%); }
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover{
  transform:translateY(-2px); border-color:var(--amber); box-shadow:0 8px 24px rgba(255,183,3,.26); }
.stButton > button:active{ transform:scale(.98); }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"]{
  background:linear-gradient(135deg,var(--amber),var(--orange)); border:none; }
.stButton > button[kind="primary"] *, [data-testid="stFormSubmitButton"] > button[kind="primary"] *{ color:#021b29 !important; font-weight:700; }
a[data-testid="stPageLink-NavLink"]{ border-radius:12px; border:1px solid var(--line); background:rgba(255,255,255,.05);
  transition:transform .2s, background .2s, border-color .2s; }
a[data-testid="stPageLink-NavLink"]:hover{ transform:translateY(-2px); border-color:var(--amber); background:rgba(255,183,3,.12); }
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"]{ border-radius:12px; transition:box-shadow .2s; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:hover{ box-shadow:0 0 0 2px rgba(255,183,3,.55); }
[data-testid="stAlert"]{ border-radius:14px; border-left:4px solid var(--orange); background:var(--glass-hi) !important; }
[data-testid="stDataFrame"]{ border-radius:12px; overflow:hidden; transition:box-shadow .25s; }
[data-testid="stDataFrame"]:hover{ box-shadow:0 0 0 2px rgba(33,158,188,.5); }
[data-testid="stSegmentedControl"] button[aria-checked="true"], [data-testid="stSegmentedControl"] button[aria-pressed="true"]{ box-shadow:0 0 14px rgba(255,183,3,.35); }
[data-testid="stSidebar"]{ background:linear-gradient(180deg,#021e2d,#01141f); border-right:1px solid var(--line); }
[data-testid="stSidebar"] a{ transition:transform .2s, background .2s; }
[data-testid="stSidebar"] a:hover{ transform:translateX(5px); background:rgba(255,183,3,.15); }
.step-n{ display:inline-grid; place-items:center; width:26px; height:26px; border-radius:50%; background:var(--amber); color:#021b29; font-weight:700; margin-right:8px; }
.step-t{ font-family:var(--disp); font-weight:700; font-size:1.1rem; } .step-d{ color:var(--mut); font-size:.9rem; margin:6px 0 10px; }

/* tiles (small cards): the only place that lifts on hover */
[class*="st-key-tile-"]{ padding:1rem 1.1rem !important; animation:rise .55s cubic-bezier(.2,.8,.2,1) backwards;
  transition:transform .28s cubic-bezier(.2,.8,.2,1), box-shadow .28s, border-color .28s, background .28s; }
[class*="st-key-tile-"]:hover{ transform:translateY(-5px); background:var(--glass-hi); border-color:rgba(255,183,3,.8);
  box-shadow:0 18px 38px rgba(1,14,22,.5), 0 0 28px rgba(255,183,3,.2); }

/* loader + skeleton */
[data-testid="stSpinner"]{ display:flex; align-items:center; gap:10px; color:var(--sky); }
[data-testid="stSpinner"] svg, [data-testid="stSpinner"] i{ display:none !important; }
[data-testid="stSpinner"]::before{ content:""; width:24px; height:24px; flex:none;
  background:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><polygon points='13 2 4 14 12 14 11 22 20 10 12 10 13 2' fill='%23ffb703'/></svg>") center/contain no-repeat;
  filter:drop-shadow(0 0 6px #ffb703); animation:zap 1s ease-in-out infinite; }
.vega-embed, .vega-embed canvas, .vega-embed svg{ background:transparent !important; }

@keyframes rise{ from{ opacity:0; transform:translateY(16px);} to{ opacity:1; transform:none;} }
@keyframes slideIn{ from{ opacity:0; transform:translateX(-16px);} to{ opacity:1; transform:none;} }
@keyframes glow{ 0%,100%{ box-shadow:0 0 16px rgba(255,183,3,.4);} 50%{ box-shadow:0 0 32px rgba(251,133,0,.8);} }
@keyframes pulse{ 0%,100%{ opacity:1; transform:scale(1);} 50%{ opacity:.35; transform:scale(.7);} }
@keyframes blink{ 0%,100%{ opacity:1;} 50%{ opacity:.35;} }
@keyframes zap{ 0%,100%{ opacity:.45; transform:scale(.9);} 40%{ opacity:1; transform:scale(1.12);} 60%{ opacity:.7;} }
@keyframes draw{ to{ stroke-dashoffset:0; } }

@media (prefers-reduced-motion: reduce){
  *, *::before, *::after{ animation:none !important; transition:none !important; scroll-behavior:auto !important; }
  .spark .ln{ stroke-dashoffset:0; }
}
"""


@lru_cache(maxsize=1)
def _css_cached() -> str:
    svg64 = base64.b64encode(_pole_scene_svg().encode()).decode()
    return _CSS.replace("__SCENE__", svg64)


def apply_theme() -> None:
    """Inject the global stylesheet. Call once at the top of every page."""
    st.markdown(f"<style>{_css_cached()}</style>", unsafe_allow_html=True)


def page_header(icon_name: str, title: str, description: str = "") -> None:
    st.html(f'<div class="ph"><div class="ph-icon">{icon(icon_name, 22)}</div>'
            f'<div><h1>{esc(title)}</h1><p>{esc(description)}</p></div></div>')


def tip(text: str) -> None:
    st.html(f'<details class="tip"><summary>{icon("bolt", 13)} Hint</summary><div>{esc(text)}</div></details>')


def eyebrow(text: str) -> None:
    st.html(f'<div class="eyebrow">{esc(text)}</div>')


def step_card_header(number: int, title: str, description="") -> None:
    desc = "" if description is Ellipsis else esc(str(description))
    st.html(f'<div><span class="step-n">{number}</span><span class="step-t">{esc(title)}</span></div>'
            f'<div class="step-d">{desc}</div>')


def style_chart(chart):
    """Shared dark chart theme for every Altair chart."""
    try:
        return (chart.configure(background="transparent")
                .configure_axis(labelColor="#cfe9f5", titleColor=SKY, gridColor="rgba(142,202,230,.12)",
                                domainColor="rgba(142,202,230,.30)", tickColor="rgba(142,202,230,.30)",
                                labelFont="Inter", titleFont="Inter")
                .configure_legend(labelColor="#cfe9f5", titleColor=SKY, orient="top")
                .configure_view(stroke=None))
    except Exception:
        return chart
