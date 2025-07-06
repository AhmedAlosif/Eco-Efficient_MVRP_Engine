import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import math
import pandas as pd
import random

# Optional: suppress Overpass area warnings
try:
    import osmnx._overpass as oxa
    oxa.MAX_QUERY_AREA_SIZE = float("inf")
except ImportError:
    pass

st.set_page_config(page_title="Tiled OSM Downloader", layout="wide")
st.title("🗺️ Tiled OSM Downloader with RAM Estimation + Export")

TILE_SIZE_DEG = 0.009
MAX_TILES_HARD_LIMIT = 50
RAM_SAFETY_FACTOR = 3
SAMPLE_TILE_COUNT = 5

# ----------------- GEOJSON UPLOAD SECTION -----------------
st.subheader("📁 Import GeoJSON File")

uploaded_file = st.file_uploader("Upload a GeoJSON file to view it on the map", type=["geojson", "json"])

if uploaded_file is not None:
    try:
        gdf_uploaded = gpd.read_file(uploaded_file)
        # Convert datetime columns to strings for JSON serialization
        for col in gdf_uploaded.columns:
            if pd.api.types.is_datetime64_any_dtype(gdf_uploaded[col]):
                gdf_uploaded[col] = gdf_uploaded[col].astype(str)

        # Project to UTM for accurate centroid
        utm_crs = gdf_uploaded.estimate_utm_crs()
        center_point = gdf_uploaded.to_crs(utm_crs).geometry.centroid.unary_union.centroid
        center = gpd.GeoSeries([center_point], crs=utm_crs).to_crs(epsg=4326).geometry.iloc[0]
        center_latlon = [center.y, center.x]

        m = folium.Map(location=center_latlon, zoom_start=13)
        folium.GeoJson(gdf_uploaded).add_to(m)
        st_folium(m, width=1700, height=500, key="uploaded_map")

    except Exception as e:
        st.error(f"Error loading GeoJSON: {e}")

# ----------------- OSM DOWNLOADER SECTION -----------------

st.subheader("🌐 Download OSM Data for a Location")

def get_tiles(bounds, tile_size_deg):
    north, south, east, west = bounds
    lat_steps = math.ceil((north - south) / tile_size_deg)
    lon_steps = math.ceil((east - west) / tile_size_deg)
    tiles = []
    for i in range(lat_steps):
        for j in range(lon_steps):
            n = north - i * tile_size_deg
            s = max(n - tile_size_deg, south)
            w = west + j * tile_size_deg
            e = min(w + tile_size_deg, east)
            tiles.append((n, s, e, w))
    return tiles

def fetch_sample_tiles(tags, bounds, tile_size_deg, n_samples):
    tiles = get_tiles(bounds, tile_size_deg)
    n_samples = min(n_samples, len(tiles))
    sampled_tiles = random.sample(tiles, n_samples)
    sizes = []
    for (n, s, e, w) in sampled_tiles:
        try:
            gdf = ox.features_from_bbox((w, s, e, n), tags)
            ram_mb = gdf.memory_usage(deep=True).sum() / (1024 ** 2)
            sizes.append(ram_mb)
        except Exception as e:
            st.warning(f"Sample tile fetch failed: {e}")
    return sizes if sizes else [1]

with st.form("location_form"):
    location_input = st.text_input("📍 Enter a location (e.g. 'Central Park Zoo, New York, USA')")
    available_tags = ["building", "highway", "landuse", "natural", "amenity", "leisure", "railway"]
    selected_tags_input = st.multiselect("🏷️ Select feature types to download:", available_tags, default=["highway"])
    submitted = st.form_submit_button("🔍 Submit")

if submitted:
    st.session_state["location"] = location_input
    st.session_state["tags"] = selected_tags_input
    st.session_state["confirmed"] = False
    st.session_state.pop("confirm_radio", None)

location = st.session_state.get("location", "")
selected_tags = st.session_state.get("tags", [])

if location and selected_tags:
    try:
        bounds_array = ox.geocode_to_gdf(location).total_bounds
        west, south, east, north = bounds_array

        tags = {tag: True for tag in selected_tags}
        tiles = get_tiles((north, south, east, west), TILE_SIZE_DEG)

        sample_ram_list = fetch_sample_tiles(tags, (north, south, east, west), TILE_SIZE_DEG, SAMPLE_TILE_COUNT)
        avg_sample_ram_mb = sum(sample_ram_list) / len(sample_ram_list)
        estimated_ram = avg_sample_ram_mb * len(tiles) * RAM_SAFETY_FACTOR

        st.write(f"📐 **Area bounds:** {round(north,4)}, {round(south,4)}, {round(east,4)}, {round(west,4)}")
        st.write(f"🧱 **Total tiles:** {len(tiles)}")
        st.write(f"🧠 **Estimated RAM usage:** ~{estimated_ram:.2f} MB (×{RAM_SAFETY_FACTOR})")

        if len(tiles) > MAX_TILES_HARD_LIMIT:
            st.warning(f"⚠️ Too many tiles! Limiting to {MAX_TILES_HARD_LIMIT}.")
            tiles = tiles[:MAX_TILES_HARD_LIMIT]

        if len(tiles) > 1:
            max_tiles = st.slider(
                "🔢 Limit number of tiles to fetch",
                min_value=1,
                max_value=len(tiles),
                value=len(tiles)
            )
            tiles = tiles[:max_tiles]
        else:
            st.info("Only 1 tile found.")

        confirm = st.radio(
            "Do you want to proceed with the download?",
            ("No", "Yes"),
            index=0,
            key="confirm_radio"
        )

        if confirm == "Yes":
            st.session_state["confirmed"] = True
        else:
            st.stop()

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()

if st.session_state.get("confirmed", False):
    all_gdfs = []
    status = st.empty()

    for i, (n, s, e, w) in enumerate(tiles):
        status.text(f"📡 Downloading tile {i+1} of {len(tiles)}...")
        try:
            gdf_tile = ox.features_from_bbox((w, s, e, n), tags)
            if not gdf_tile.empty:
                all_gdfs.append(gdf_tile)
        except Exception as e:
            st.warning(f"Tile {i+1} failed: {e}")

    status.text("✅ Download complete!")

    # ✅ Prevent re-download on map interaction
    st.session_state["confirmed"] = False

    if all_gdfs:
        full_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)

        # Accurate centroid
        utm_crs = full_gdf.estimate_utm_crs()
        full_gdf_proj = full_gdf.to_crs(utm_crs)
        centroid_proj = full_gdf_proj.geometry.centroid
        mean_x = centroid_proj.x.mean()
        mean_y = centroid_proj.y.mean()
        center_point = gpd.GeoSeries([gpd.points_from_xy([mean_x], [mean_y])[0]], crs=utm_crs).to_crs(epsg=4326)
        center = [center_point.geometry.y.iloc[0], center_point.geometry.x.iloc[0]]

        m = folium.Map(location=center, zoom_start=14)
        folium.GeoJson(full_gdf).add_to(m)
        st_folium(m, width=1700, height=500, key="final_map")

        st.success(f"✅ {len(full_gdf)} features downloaded across {len(tiles)} tiles.")

        geojson_str = full_gdf.to_json()
        st.download_button(
            label="📁 Download GeoJSON",
            data=geojson_str,
            file_name="osm_features.geojson",
            mime="application/geo+json"
        )
    else:
        st.warning("⚠️ No data returned from tiles.")
