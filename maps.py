"""Shared map helpers for both GIS pages (opaque street tiles + circle markers)."""
from html import escape as esc
import re

import folium

AMBER, TEAL, SKY, ORANGE, GRAY = "#ffb703", "#219ebc", "#8ecae6", "#fb8500", "#7f93a0"

_MAP_CSS = """<style>
@keyframes gm-ring{0%{transform:scale(.5);opacity:.9}100%{transform:scale(2.6);opacity:0}}
.gm-pulse{position:relative;width:16px;height:16px;border-radius:50%;background:#fb8500;box-shadow:0 0 12px #fb8500}
.gm-pulse:after{content:'';position:absolute;inset:0;border-radius:50%;border:2px solid #fb8500;animation:gm-ring 1.6s ease-out infinite}
.gm-pulse.gm-user{background:#ffb703;box-shadow:0 0 12px #ffb703}
.gm-pulse.gm-user:after{border-color:#ffb703}
.leaflet-popup-content-wrapper,.leaflet-popup-tip{background:#04283a;color:#e8f4fa;border:1px solid rgba(142,202,230,.3)}
html,body,.leaflet-container{background:#0b1d29!important}
.leaflet-tile{opacity:.38!important;filter:saturate(.72)}
.leaflet-container{font-family:Inter,Segoe UI,sans-serif}
</style>"""


def barangay_key(value):
    """Normalize an address or incident location to its barangay name."""
    name = (value or "").split(",", maxsplit=1)[0].strip().lower()
    return re.sub(r"^(barangay|brgy\.?)\s*", "", name).strip()


def household_position(household, households):
    """Return saved coordinates or a same-barangay estimate and its accuracy flag."""
    lat, lon = household["latitude"], household["longitude"]
    if lat is not None and lon is not None:
        is_synthetic = (household["homeowner_name"] or "").startswith("Synthetic ")
        return lat, lon, is_synthetic

    key = barangay_key(household["address"])
    points = [
        (row["latitude"], row["longitude"])
        for row in households
        if row["latitude"] is not None and row["longitude"] is not None
        and key and barangay_key(row["address"]) == key
    ]
    if not points:
        return None
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
        True,
    )


def base_map(center, zoom):
    m = folium.Map(location=center, zoom_start=zoom, tiles=None,
                   control_scale=True, zoom_control=True)
    folium.TileLayer(
        tiles="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors",
        name="OpenStreetMap",
    ).add_to(m)
    m.get_root().header.add_child(folium.Element(_MAP_CSS))
    return m


def coordinate_text(lat, lon):
    return f"{float(lat):.6f}, {float(lon):.6f}"


def popup(title, lines, accent=SKY, width=220):
    body = "".join(f'<div style="margin-top:3px"><span style="opacity:.6">{esc(k)}</span> '
                   f'<b>{esc(str(v))}</b></div>' for k, v in lines)
    html = (f'<div style="font:12px Inter,Segoe UI,sans-serif;width:{width}px">'
            f'<div style="color:{accent};font-weight:700;font-size:13px">{esc(title)}</div>{body}</div>')
    return folium.Popup(html, max_width=width + 40)


def dot(m, lat, lon, color, radius, tooltip, pop=None, fill=0.85, weight=2, pulse=False):
    if pulse:
        folium.Marker(
            [lat, lon], popup=pop, tooltip=tooltip,
            icon=folium.DivIcon(html='<div class="gm-pulse gm-user"></div>',
                                icon_size=(16, 16), icon_anchor=(8, 8)),
        ).add_to(m)
        return
    folium.CircleMarker(
        location=[lat, lon], radius=radius, color=color, weight=weight,
        fill=True, fill_color=color, fill_opacity=fill, popup=pop, tooltip=tooltip,
    ).add_to(m)


def hazard(m, lat, lon, severity, tooltip, pop=None):
    """Render incidents at every severity as pulsing orange map markers."""
    size = {"High": 20, "Medium": 16, "Low": 13}.get(severity, 16)
    folium.Marker(
        [lat, lon], popup=pop, tooltip=tooltip,
        icon=folium.DivIcon(
            html=f'<div class="gm-pulse" style="width:{size}px;height:{size}px"></div>',
            icon_size=(size, size), icon_anchor=(size // 2, size // 2),
        ),
    ).add_to(m)


def legend(m, items):
    rows = "".join(f'<div><span style="color:{c}">&#9679;</span> {esc(t)}</div>' for c, t in items)
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;bottom:18px;left:14px;z-index:9999;padding:9px 13px;border-radius:12px;'
        'background:rgba(2,26,40,.9);border:1px solid rgba(142,202,230,.3);color:#e8f4fa;'
        f'font:12px/1.6 Inter,Segoe UI,sans-serif">{rows}</div>'))


def render(m, height=520):
    """st_folium wrapper that tolerates older streamlit-folium versions."""
    from streamlit_folium import st_folium
    try:
        return st_folium(m, use_container_width=True, height=height, returned_objects=[])
    except TypeError:
        return st_folium(m, width=900, height=height, returned_objects=[])
