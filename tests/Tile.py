import streamlit as st
import osmnx as ox
import folium
from shapely.geometry import box
from streamlit_folium import st_folium
import geopandas as gpd
import math
import pandas as pd
import tempfile
import io

st.title("Tiled OSM Downloader with RAM Estimation + Export")

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

def fetch_sample_tile(tags):
    sample_bbox = (48.8566, 48.8526, 2.3522, 2.3482)  # ~1km² in Paris
    return ox.features_from_bbox(sample_bbox, tags=tags)

# --- UI
location = st.text_input("Enter a location (e.g. 'Paris, France')")

# Tag selection
available_tags = ["building", "highway", "landuse", "natural", "amenity", "leisure", "railway"]
selected_tags = st.multiselect("Select feature types to download:", available_tags, default=["highway"])

if location and selected_tags:
    try:
        place_gdf = ox.geocode_to_gdf(location)
        geom = place_gdf.geometry.iloc[0]
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        west, south, east, north = bounds
        tile_size_deg = 0.009  # ≈ 1 km

        # Construct tag query
        tags = {tag: True for tag in selected_tags}

        # Estimate RAM
        sample_gdf = fetch_sample_tile(tags)
        sample_ram_mb = sample_gdf.memory_usage(deep=True).sum() / (1024 ** 2)
        tiles = get_tiles((north, south, east, west), tile_size_deg)
        estimated_ram = sample_ram_mb * len(tiles)

        choice = st.radio(
            f"This will fetch {len(tiles)} tiles (~{estimated_ram:.2f} MB estimated RAM). Continue?",
            ("Yes", "No")
        )

        if choice == "Yes":
            all_gdfs = []
            with st.spinner("Downloading tiles..."):
                for i, (n, s, e, w) in enumerate(tiles):
                    try:
                        tile_gdf = ox.features_from_bbox((n, s, e, w), tags)
                        if not tile_gdf.empty:
                            all_gdfs.append(tile_gdf)
                    except Exception as e:
                        st.warning(f"Tile {i+1} failed: {e}")

            if all_gdfs:
                # Merge into single GeoDataFrame
                full_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
                center = [full_gdf.geometry.centroid.y.mean(), full_gdf.geometry.centroid.x.mean()]
                m = folium.Map(location=center, zoom_start=12)
                folium.GeoJson(full_gdf).add_to(m)
                st_folium(m, width=700, height=500)

                st.success(f"Fetched {len(full_gdf)} features across {len(tiles)} tiles.")

                # Download button
                geojson_str = full_gdf.to_json()
                st.download_button(
                    label="📁 Download GeoJSON",
                    data=geojson_str,
                    file_name="osm_features.geojson",
                    mime="application/geo+json"
                )
            else:
                st.warning("No data found in any tiles.")
        else:
            st.session_state["location_input"] = ""

    except Exception as e:
        st.error(f"Error: {e}")