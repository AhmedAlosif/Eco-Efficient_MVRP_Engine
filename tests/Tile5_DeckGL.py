import dash
from dash import html, dcc
import dash_deck
import dash_bootstrap_components as dbc
import pandas as pd
import geopandas as gpd
import pyarrow.parquet as pq
import pydeck as pdk
import json

# Sample Parquet file (should contain geometry)
PARQUET_PATH = "/path/to/your_file.parquet"

# Load parquet as GeoDataFrame
try:
    gdf = gpd.read_parquet(PARQUET_PATH)
    gdf = gdf.to_crs(epsg=4326)
    gdf = gdf[gdf.geometry.type == "Point"]  # Use only Points for this example
    gdf["lon"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y
except Exception as e:
    raise RuntimeError(f"Error reading Parquet file: {e}")

# Create pydeck layer
layer = {
    "id": "scatter-layer",
    "type": "ScatterplotLayer",
    "data": gdf.to_dict("records"),
    "get_position": "[lon, lat]",
    "get_color": "[200, 30, 0, 160]",
    "get_radius": 40,
}

# Create pydeck view state
view_state = pdk.ViewState(
    longitude=gdf["lon"].mean(),
    latitude=gdf["lat"].mean(),
    zoom=12,
    pitch=0
)

# Build pydeck object
r = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"text": "Latitude: {lat}\nLongitude: {lon}"}
)

# App layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H2("🗺️ Dash + Deck.GL Parquet Viewer"),
    dash_deck.DeckGL(
        id="deck-map",
        mapboxKey="",  # Optional if you use a map style that doesn't need Mapbox
        data=json.loads(r.to_json())
    )
], fluid=True)

if __name__ == '__main__':
    app.run(debug=True)
