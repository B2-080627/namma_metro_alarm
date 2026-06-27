import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import base64

st.set_page_config(page_title="Namma Metro GPS Alarm", page_icon="🚇", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("namma_metro_stations1.csv")
    df.columns = [c.strip() for c in df.columns]
    df["latitude"]  = pd.to_numeric(df["latitude"])
    df["longitude"] = pd.to_numeric(df["longitude"])
    return df

df = load_data()

alarm_distance = st.sidebar.slider("Alarm Distance (meters)", 100, 2000, 500, 100)
st.sidebar.markdown("---")

# ── Custom alarm sound ──────────────────────────────────────────────────────
st.sidebar.markdown("### 🔔 Custom Alarm Sound")
uploaded_alarm = st.sidebar.file_uploader(
    "Upload alarm sound (MP3 / OGG / WAV)",
    type=["mp3", "ogg", "wav"],
    help="Leave empty to use the built-in alarm"
)

custom_b64   = ""
custom_mime  = ""
if uploaded_alarm:
    raw = uploaded_alarm.read()
    custom_b64  = base64.b64encode(raw).decode()
    ext = uploaded_alarm.name.rsplit(".", 1)[-1].lower()
    custom_mime = {"mp3": "audio/mpeg", "ogg": "audio/ogg", "wav": "audio/wav"}.get(ext, "audio/mpeg")
    st.sidebar.success(f"✅ Loaded: {uploaded_alarm.name}")

st.sidebar.markdown("---")
st.sidebar.caption("💡 Search and select your destination station directly on the map panel.")

stations_json = df[["Name","latitude","longitude"]].rename(
    columns={"Name":"name","latitude":"lat","longitude":"lon"}
).to_json(orient="records")

html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<!-- NoSleep prevents screen / browser tab from sleeping -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/nosleep/0.12.0/NoSleep.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f1117;color:#e2e8f0;
      display:flex;flex-direction:column;height:100vh;overflow:hidden;}}

/* ── TOP BAR ── */
.topbar{{
  display:flex;align-items:center;gap:10px;
  padding:10px 14px;background:#1a1d27;border-bottom:1px solid #2d3147;
  flex-shrink:0;flex-wrap:wrap;
}}
.brand{{font-size:.95rem;font-weight:700;color:#fff;display:flex;align-items:center;gap:7px;white-space:nowrap;}}
.pulse{{width:10px;height:10px;border-radius:50%;background:#4ade80;opacity:0;transition:opacity .3s;flex-shrink:0;}}
.pulse.on{{opacity:1;animation:blink 1.5s infinite;}}
@keyframes blink{{0%,100%{{box-shadow:0 0 0 0 rgba(74,222,128,.5)}}50%{{box-shadow:0 0 0 6px rgba(74,222,128,0)}}}}

/* ── SEARCH ── */
.search-wrap{{position:relative;flex:1;min-width:180px;max-width:320px;}}
.search-input{{
  width:100%;padding:7px 12px;border-radius:8px;border:1.5px solid #334155;
  background:#0f1117;color:#e2e8f0;font-size:.85rem;outline:none;transition:border-color .2s;
}}
.search-input:focus{{border-color:#4ade80;}}
.search-input::placeholder{{color:#475569;}}
.dropdown{{
  position:absolute;top:calc(100% + 4px);left:0;right:0;
  background:#1e293b;border:1px solid #334155;border-radius:8px;
  max-height:220px;overflow-y:auto;z-index:9999;display:none;
  box-shadow:0 8px 24px rgba(0,0,0,.5);
}}
.dropdown.open{{display:block;}}
.dropdown-item{{
  padding:8px 12px;font-size:.82rem;cursor:pointer;color:#cbd5e1;
  border-bottom:1px solid #1a1d27;transition:background .15s;
}}
.dropdown-item:last-child{{border-bottom:none;}}
.dropdown-item:hover,.dropdown-item.active{{background:#334155;color:#fff;}}
.dropdown-item mark{{background:transparent;color:#4ade80;font-weight:700;}}
.no-results{{padding:8px 12px;font-size:.82rem;color:#475569;font-style:italic;}}

/* ── STATS ── */
.stats{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;}}
.stat{{display:flex;flex-direction:column;}}
.slabel{{font-size:.58rem;text-transform:uppercase;letter-spacing:.08em;color:#475569;}}
.sval{{font-size:.8rem;font-weight:600;color:#cbd5e1;font-variant-numeric:tabular-nums;}}
.sval.green{{color:#4ade80;}} .sval.yellow{{color:#fbbf24;}} .sval.red{{color:#f87171;}}

/* ── BUTTONS ── */
.btn{{padding:7px 14px;border:none;border-radius:6px;font-size:.82rem;font-weight:600;
      cursor:pointer;transition:background .2s,transform .1s;white-space:nowrap;}}
.btn:active{{transform:scale(.97);}}
.btn-go{{background:#4ade80;color:#0f1117;}} .btn-go:hover{{background:#22c55e;}}
.btn-stop{{background:#f87171;color:#fff;}} .btn-stop:hover{{background:#ef4444;}}
.btn-sm{{background:#1e293b;color:#94a3b8;padding:6px 10px;}} .btn-sm:hover{{background:#334155;}}

/* ── KEEP-ALIVE BADGE ── */
.ka{{
  font-size:.62rem;padding:3px 8px;border-radius:10px;
  background:#1e293b;color:#475569;border:1px solid #2d3147;
  white-space:nowrap;transition:color .3s,border-color .3s;
}}
.ka.live{{color:#4ade80;border-color:#166534;}}

/* ── STATUS BAR ── */
.statusbar{{
  padding:5px 14px;font-size:.72rem;background:#141720;
  border-bottom:1px solid #2d3147;color:#64748b;flex-shrink:0;min-height:26px;
  display:flex;align-items:center;gap:6px;
}}
.statusbar.ok{{color:#4ade80;}} .statusbar.warn{{color:#fbbf24;}} .statusbar.err{{color:#f87171;}}

/* ── ALARM BANNER ── */
.alarm{{display:none;padding:10px 14px;font-size:.88rem;font-weight:700;text-align:center;flex-shrink:0;}}
.alarm.approaching{{display:block;background:#78350f;color:#fde68a;}}
.alarm.arriving{{display:block;background:#14532d;color:#86efac;animation:flashbg 1s infinite alternate;}}
@keyframes flashbg{{from{{background:#14532d;}}to{{background:#166534;}}}}

/* ── MAP ── */
#map{{flex:1;width:100%;}}

/* ── BOTTOM BAR ── */
.infobar{{
  display:flex;align-items:center;justify-content:space-between;
  padding:6px 14px;background:#1a1d27;border-top:1px solid #2d3147;
  flex-shrink:0;gap:10px;flex-wrap:wrap;
}}
.infobar-stat{{display:flex;flex-direction:column;align-items:center;}}
.infobar-label{{font-size:.58rem;text-transform:uppercase;letter-spacing:.07em;color:#475569;}}
.infobar-val{{font-size:.8rem;font-weight:600;color:#e2e8f0;font-variant-numeric:tabular-nums;}}
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <div class="brand">
    <span class="pulse" id="pulse"></span>
    🚇 Metro Alarm
  </div>

  <div class="search-wrap" id="searchWrap">
    <input class="search-input" id="searchInput"
      type="text" placeholder="🔍 Search destination station…"
      autocomplete="off"
      oninput="onSearch()" onkeydown="onKey(event)" onfocus="openDropdown()"/>
    <div class="dropdown" id="dropdown"></div>
  </div>

  <div class="stats">
    <div class="stat"><span class="slabel">Nearest Station</span><span class="sval green" id="sNearest">—</span></div>
    <div class="stat"><span class="slabel">Destination</span><span class="sval red" id="sDest">Not set</span></div>
    <div class="stat"><span class="slabel">Distance Left</span><span class="sval yellow" id="sDist">—</span></div>
    <div class="stat"><span class="slabel">Accuracy</span><span class="sval" id="sAcc">—</span></div>
  </div>

  <div style="display:flex;gap:7px;align-items:center;">
    <button class="btn btn-go" id="btnTrack" onclick="toggleTracking()">▶ Start</button>
    <button class="btn btn-sm" onclick="centerMap()">⊙</button>
    <span class="ka" id="kaBadge">⏳ standby</span>
  </div>
</div>

<!-- STATUS -->
<div class="statusbar" id="statusbar">Search a destination station, then press Start.</div>

<!-- ALARM -->
<div class="alarm" id="alarmBanner"></div>

<!-- MAP -->
<div id="map"></div>

<!-- BOTTOM BAR -->
<div class="infobar">
  <div class="infobar-stat"><span class="infobar-label">Alarm radius</span><span class="infobar-val">{alarm_distance} m</span></div>
  <div class="infobar-stat"><span class="infobar-label">Destination</span><span class="infobar-val" id="iDest">—</span></div>
  <div class="infobar-stat"><span class="infobar-label">Lat</span><span class="infobar-val" id="iLat">—</span></div>
  <div class="infobar-stat"><span class="infobar-label">Lon</span><span class="infobar-val" id="iLon">—</span></div>
  <div class="infobar-stat"><span class="infobar-label">Updates</span><span class="infobar-val" id="iCount">0</span></div>
  <div class="infobar-stat"><span class="infobar-label">Active</span><span class="infobar-val" id="iKa">—</span></div>
</div>

<!-- AUDIO — swapped to custom sound by JS if uploaded -->
<audio id="alarmAudio" loop>
  <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg"/>
</audio>

<script>
// ── STATION DATA ──
const STATIONS   = {stations_json};
const ALARM_DIST = {alarm_distance};

// ── CUSTOM ALARM SOUND (base64-injected by Python when uploaded) ──
const CUSTOM_B64  = "{custom_b64}";
const CUSTOM_MIME = "{custom_mime}";
if (CUSTOM_B64) {{
  const a = document.getElementById('alarmAudio');
  a.src = 'data:' + CUSTOM_MIME + ';base64,' + CUSTOM_B64;
  a.load();
}}

// ── MAP ──
const map = L.map('map',{{zoomControl:true}}).setView([12.9716,77.5946],13);
const streetLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution:'© OpenStreetMap',maxZoom:19}}).addTo(map);
const satLayer = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{attribution:'Esri',maxZoom:19}});
L.control.layers({{'Street':streetLayer}},{{'Satellite':satLayer}}).addTo(map);

STATIONS.forEach(s=>{{
  L.circleMarker([s.lat,s.lon],{{
    radius:5,color:'#60a5fa',fillColor:'#3b82f6',fillOpacity:.8,weight:1.5
  }}).addTo(map).bindTooltip(s.name);
}});

// ── DESTINATION STATE ──
let destLat=null,destLon=null,destName=null;
let destMarker=null,alarmRing=null,routeLine=null;

const destIcon=L.divIcon({{
  className:'',
  html:`<div style="width:22px;height:22px;border-radius:50%;background:#f87171;
        border:3px solid #fff;box-shadow:0 0 0 3px rgba(248,113,113,.4);
        display:flex;align-items:center;justify-content:center;font-size:11px;">🏁</div>`,
  iconSize:[22,22],iconAnchor:[11,11]
}});

function setDestination(station) {{
  destLat=station.lat; destLon=station.lon; destName=station.name;
  if (destMarker) map.removeLayer(destMarker);
  if (alarmRing)  map.removeLayer(alarmRing);
  destMarker=L.marker([destLat,destLon],{{icon:destIcon}})
    .addTo(map).bindPopup('<b>Destination</b><br>'+destName);
  alarmRing=L.circle([destLat,destLon],{{
    radius:ALARM_DIST,color:'#f87171',fillColor:'#f87171',
    fillOpacity:.07,weight:1.5,dashArray:'6 4'
  }}).addTo(map);
  map.setView([destLat,destLon],14);
  document.getElementById('sDest').textContent=destName;
  document.getElementById('iDest').textContent=destName;
  setStatus('Destination set: '+destName+'. Press Start to track your location.','ok');
  alarmFired=false;
  document.getElementById('alarmBanner').className='alarm';
}}

// ── AUTOCOMPLETE ──
let activeIdx=-1,filtered=[];

function onSearch(){{
  const q=document.getElementById('searchInput').value.trim().toLowerCase();
  activeIdx=-1;
  if(!q){{filtered=[];renderDropdown([],'');closeDropdown();return;}}
  filtered=STATIONS.filter(s=>s.name.toLowerCase().includes(q));
  renderDropdown(filtered,q); openDropdown();
}}
function renderDropdown(list,q){{
  const dd=document.getElementById('dropdown');
  if(!list.length){{dd.innerHTML='<div class="no-results">No stations found</div>';return;}}
  dd.innerHTML=list.slice(0,12).map((s,i)=>{{
    const hi=s.name.replace(new RegExp('('+q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')+')','gi'),'<mark>$1</mark>');
    return `<div class="dropdown-item" data-idx="${{i}}" onmousedown="pickStation(${{i}})">${{hi}}</div>`;
  }}).join('');
}}
function openDropdown(){{if(document.getElementById('dropdown').innerHTML)document.getElementById('dropdown').classList.add('open');}}
function closeDropdown(){{document.getElementById('dropdown').classList.remove('open');activeIdx=-1;}}
function pickStation(idx){{
  const s=filtered[idx]; if(!s) return;
  document.getElementById('searchInput').value=s.name;
  closeDropdown(); setDestination(s);
}}
function onKey(e){{
  const items=document.querySelectorAll('.dropdown-item');
  if(e.key==='ArrowDown'){{activeIdx=Math.min(activeIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('active',i===activeIdx));e.preventDefault();}}
  else if(e.key==='ArrowUp'){{activeIdx=Math.max(activeIdx-1,0);items.forEach((el,i)=>el.classList.toggle('active',i===activeIdx));e.preventDefault();}}
  else if(e.key==='Enter'){{if(activeIdx>=0)pickStation(activeIdx);else if(filtered.length)pickStation(0);e.preventDefault();}}
  else if(e.key==='Escape')closeDropdown();
}}
document.addEventListener('mousedown',e=>{{if(!document.getElementById('searchWrap').contains(e.target))closeDropdown();}});

// ── USER TRACKING ──
const userIcon=L.divIcon({{
  className:'',
  html:`<div style="width:18px;height:18px;border-radius:50%;background:#4ade80;
        border:3px solid #fff;box-shadow:0 0 0 3px rgba(74,222,128,.4);"></div>`,
  iconSize:[18,18],iconAnchor:[9,9]
}});

let userMarker=null,accCircle=null,trackPolyline=null;
let trackPoints=[],watchId=null,tracking=false,firstFix=true;
let updateCount=0,alarmFired=false;

function setStatus(msg,cls=''){{
  const el=document.getElementById('statusbar');
  el.textContent=msg; el.className='statusbar '+cls;
}}
function haversineM(lat1,lon1,lat2,lon2){{
  const R=6371000,dLat=(lat2-lat1)*Math.PI/180,dLon=(lon2-lon1)*Math.PI/180;
  const a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
}}
function nearestStation(lat,lon){{
  let best=null,bestD=Infinity;
  STATIONS.forEach(s=>{{const d=haversineM(lat,lon,s.lat,s.lon);if(d<bestD){{bestD=d;best=s;}}}});
  return best;
}}

// ── KEEP-ALIVE (NoSleep + heartbeat every 25 s) ──────────────────────────
const noSleep = new NoSleep();
let kaTimer = null, kaSeconds = 0;

function startKeepAlive() {{
  noSleep.enable();                       // prevents screen & tab sleep
  kaSeconds = 0;
  const badge = document.getElementById('kaBadge');
  const iKa   = document.getElementById('iKa');
  kaTimer = setInterval(() => {{
    kaSeconds += 25;
    const m = Math.floor(kaSeconds / 60), s = kaSeconds % 60;
    const txt = m ? m+'m '+s+'s' : s+'s';
    badge.textContent = '🟢 ' + txt;
    badge.className   = 'ka live';
    iKa.textContent   = txt;
    // Tiny self-fetch keeps service worker + WebSocket alive
    fetch('data:text/plain,ka').catch(()=>{{}});
  }}, 25000);
}}
function stopKeepAlive() {{
  noSleep.disable();
  clearInterval(kaTimer); kaTimer = null;
  document.getElementById('kaBadge').className = 'ka';
  document.getElementById('kaBadge').textContent = '⏹ stopped';
}}

// ── CONTROLS ──
function toggleTracking(){{ if(!tracking) startTracking(); else stopTracking(); }}

function startTracking(){{
  if(!navigator.geolocation){{setStatus('Geolocation not supported.','err');return;}}
  if(!destLat){{setStatus('Please search and select a destination station first.','warn');return;}}
  tracking=true; firstFix=true; alarmFired=false;
  setStatus('Requesting location permission…','warn');
  document.getElementById('btnTrack').textContent='⏹ Stop';
  document.getElementById('btnTrack').className='btn btn-stop';
  document.getElementById('pulse').classList.add('on');
  startKeepAlive();
  watchId=navigator.geolocation.watchPosition(onPosition,onError,{{
    enableHighAccuracy:true,timeout:15000,maximumAge:0
  }});
}}
function stopTracking(){{
  if(watchId!==null){{navigator.geolocation.clearWatch(watchId);watchId=null;}}
  tracking=false;
  document.getElementById('btnTrack').textContent='▶ Start';
  document.getElementById('btnTrack').className='btn btn-go';
  document.getElementById('pulse').classList.remove('on');
  document.getElementById('alarmBanner').className='alarm';
  document.getElementById('alarmAudio').pause();
  stopKeepAlive();
  setStatus('Tracking stopped. '+updateCount+' update(s) recorded.');
}}

function onPosition(pos){{
  const lat=pos.coords.latitude,lon=pos.coords.longitude,acc=pos.coords.accuracy;
  const now=new Date();
  updateCount++;

  if(!userMarker){{
    userMarker=L.marker([lat,lon],{{icon:userIcon}}).addTo(map).bindPopup('<b>You are here</b>');
  }} else userMarker.setLatLng([lat,lon]);

  if(accCircle) map.removeLayer(accCircle);
  accCircle=L.circle([lat,lon],{{radius:acc,color:'#4ade80',fillColor:'#4ade80',fillOpacity:.08,weight:1}}).addTo(map);

  trackPoints.push([lat,lon]);
  if(trackPolyline) map.removeLayer(trackPolyline);
  if(trackPoints.length>1)
    trackPolyline=L.polyline(trackPoints,{{color:'#4ade80',weight:3,opacity:.6,dashArray:'5 4'}}).addTo(map);

  if(routeLine) map.removeLayer(routeLine);
  if(destLat) routeLine=L.polyline([[lat,lon],[destLat,destLon]],{{
    color:'#f87171',weight:2,opacity:.5,dashArray:'8 5'
  }}).addTo(map);

  const ns=nearestStation(lat,lon);
  const distM=destLat?haversineM(lat,lon,destLat,destLon):null;
  const distTxt=distM!==null?(distM>=1000?(distM/1000).toFixed(2)+' km':Math.round(distM)+' m'):'—';

  document.getElementById('sNearest').textContent=ns?ns.name:'—';
  document.getElementById('sDist').textContent=distTxt;
  document.getElementById('sAcc').textContent='±'+Math.round(acc)+'m';
  document.getElementById('iLat').textContent=lat.toFixed(6);
  document.getElementById('iLon').textContent=lon.toFixed(6);
  document.getElementById('iCount').textContent=updateCount;
  setStatus('Updated '+now.toLocaleTimeString()+' · ±'+Math.round(acc)+'m accuracy','ok');

  const banner=document.getElementById('alarmBanner');
  const audio=document.getElementById('alarmAudio');
  if(distM!==null){{
    if(distM<=ALARM_DIST){{
      banner.className='alarm arriving';
      banner.textContent='🔔 ARRIVING AT '+destName+' — '+Math.round(distM)+'m away!';
      if(!alarmFired){{audio.play().catch(()=>{{}});alarmFired=true;}}
    }} else if(distM<=ALARM_DIST*2){{
      banner.className='alarm approaching';
      banner.textContent='⚠ Approaching '+destName+' — '+distTxt+' remaining';
      audio.pause(); alarmFired=false;
    }} else {{
      banner.className='alarm';
      audio.pause(); alarmFired=false;
    }}
  }}

  if(firstFix){{map.setView([lat,lon],15);firstFix=false;}}
}}

function onError(err){{
  const msgs={{1:'Permission denied. Allow location in browser settings.',
               2:'Location unavailable.',3:'Request timed out.'}};
  setStatus(msgs[err.code]||'GPS error.','err');
  document.getElementById('pulse').classList.remove('on');
}}
function centerMap(){{
  if(userMarker) map.setView(userMarker.getLatLng(),15);
  else setStatus('No location yet — start tracking first.','warn');
}}
</script>
</body>
</html>
"""

st.title("🚇 Namma Metro GPS Alarm")
components.html(html, height=790, scrolling=False)
