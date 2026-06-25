import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_javascript import st_javascript
from folium.plugins import Fullscreen
from math import radians, sin, cos, sqrt, atan2

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Namma Metro GPS Alarm",
    page_icon="🚇",
    layout="wide"
)

# --------------------------------------------------
# DISTANCE FUNCTION
# --------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

# --------------------------------------------------
# LOAD CSV
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("namma_metro_stations1.csv")

    df.columns = [c.strip() for c in df.columns]

    df["latitude"] = pd.to_numeric(df["latitude"])
    df["longitude"] = pd.to_numeric(df["longitude"])

    return df

df = load_data()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🚇 Namma Metro Alarm")

source_station = st.sidebar.selectbox(
    "Current Station",
    sorted(df["Name"].unique())
)

destination_station = st.sidebar.selectbox(
    "Destination Station",
    sorted(df["Name"].unique())
)

alarm_distance = st.sidebar.slider(
    "Alarm Distance (meters)",
    100,
    2000,
    500,
    100
)

# --------------------------------------------------
# STATION COORDINATES
# --------------------------------------------------
source_row = df[df["Name"] == source_station].iloc[0]
dest_row = df[df["Name"] == destination_station].iloc[0]

source_lat = float(source_row["latitude"])
source_lon = float(source_row["longitude"])

dest_lat = float(dest_row["latitude"])
dest_lon = float(dest_row["longitude"])

# --------------------------------------------------
# GPS
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Live GPS")

gps = st_javascript("""
await new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            resolve({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude
            });
        },
        (err) => {
            resolve(null);
        },
        {
            enableHighAccuracy: true,
            timeout: 10000
        }
    );
});
""")

if gps and isinstance(gps, dict):

    current_lat = float(gps["latitude"])
    current_lon = float(gps["longitude"])

    st.sidebar.success("GPS Connected")

    st.sidebar.write(
        f"Lat: {current_lat:.6f}"
    )

    st.sidebar.write(
        f"Lon: {current_lon:.6f}"
    )

else:

    current_lat = source_lat
    current_lon = source_lon

    st.sidebar.warning(
        "GPS unavailable. Using selected current station."
    )

# --------------------------------------------------
# DISTANCES
# --------------------------------------------------
remaining_distance = haversine(
    current_lat,
    current_lon,
    dest_lat,
    dest_lon
)

journey_distance = haversine(
    source_lat,
    source_lon,
    dest_lat,
    dest_lon
)

remaining_meters = remaining_distance * 1000

# --------------------------------------------------
# NEAREST STATION
# --------------------------------------------------
df["gps_distance"] = (
    (df["latitude"] - current_lat) ** 2 +
    (df["longitude"] - current_lon) ** 2
)

nearest_station = df.loc[
    df["gps_distance"].idxmin()
]

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.title("🚇 Namma Metro GPS Alarm")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Current Station",
        source_station
    )

with col2:
    st.metric(
        "Nearest Station",
        nearest_station["Name"]
    )

with col3:
    st.metric(
        "Destination",
        destination_station
    )

with col4:
    st.metric(
        "Remaining",
        f"{remaining_distance:.2f} km"
    )

# --------------------------------------------------
# ALARM
# --------------------------------------------------
if remaining_meters <= alarm_distance:

    st.success(
        f"🔔 ARRIVING AT {destination_station}"
    )

    st.audio(
        "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"
    )

elif remaining_meters <= alarm_distance * 2:

    st.warning(
        f"⚠ Approaching {destination_station}"
    )

# --------------------------------------------------
# MAP
# --------------------------------------------------
m = folium.Map(
    location=[current_lat, current_lon],
    zoom_start=13,
    control_scale=True
)

# STREET
folium.TileLayer(
    "OpenStreetMap",
    name="Street"
).add_to(m)

# TERRAIN
folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap",
    name="Terrain"
).add_to(m)

# SATELLITE
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite"
).add_to(m)

# --------------------------------------------------
# LIVE GPS
# --------------------------------------------------
folium.Marker(
    [current_lat, current_lon],
    tooltip="Live GPS",
    popup=f"""
    <b>Current GPS Position</b><br>
    Latitude: {current_lat:.6f}<br>
    Longitude: {current_lon:.6f}
    """,
    icon=folium.Icon(color="red")
).add_to(m)

# --------------------------------------------------
# SOURCE
# --------------------------------------------------
folium.Marker(
    [source_lat, source_lon],
    tooltip="Boarding Station",
    popup=source_station,
    icon=folium.Icon(color="blue")
).add_to(m)

# --------------------------------------------------
# DESTINATION
# --------------------------------------------------
folium.Marker(
    [dest_lat, dest_lon],
    tooltip="Destination",
    popup=destination_station,
    icon=folium.Icon(color="green")
).add_to(m)

# --------------------------------------------------
# ALL STATIONS
# --------------------------------------------------
for _, row in df.iterrows():

    folium.CircleMarker(
        location=[
            row["latitude"],
            row["longitude"]
        ],
        radius=4,
        tooltip=row["Name"],
        popup=row["Name"],
        fill=True
    ).add_to(m)

# --------------------------------------------------
# ROUTE LINE
# --------------------------------------------------
folium.PolyLine(
    [
        [source_lat, source_lon],
        [dest_lat, dest_lon]
    ],
    weight=5
).add_to(m)

# --------------------------------------------------
# FULLSCREEN
# --------------------------------------------------
Fullscreen().add_to(m)

folium.LayerControl().add_to(m)

# --------------------------------------------------
# DISPLAY MAP
# --------------------------------------------------
st_folium(
    m,
    width=None,
    height=750
)

# --------------------------------------------------
# AUTO REFRESH
# --------------------------------------------------
auto = st.checkbox(
    "Auto Refresh GPS Every 10 Seconds"
)

if auto:
    import time
    time.sleep(10)
    st.rerun()