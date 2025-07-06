import os
import math
import random
import json
import pandas as pd
import geopandas as gpd
import osmnx as ox
import dash
from dash import dcc, html, Input, Output, State, ctx, callback_context
import dash_bootstrap_components as dbc
import folium
from folium import Map, GeoJson
from branca.element import Template, MacroElement
from dash.exceptions import PreventUpdate

# Constants
TILE_SIZE_DEG = 0.009
MAX_TILES_HARD_LIMIT = 50
RAM_SAFETY_FACTOR = 3
SAMPLE_TILE_COUNT = 5

# App initialization
dash_app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app = dash_app.server

# Helper functions
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
        except Exception:
            continue
    return sizes if sizes else [1]

def generate_map(gdf):
    if gdf.empty:
        return None
    utm_crs = gdf.estimate_utm_crs()
    gdf_proj = gdf.to_crs(utm_crs)
    centroid = gdf_proj.geometry.centroid.unary_union.centroid
    center = gpd.GeoSeries([centroid], crs=utm_crs).to_crs(epsg=4326).geometry.iloc[0]
    m = Map(location=[center.y, center.x], zoom_start=14)
    gdf = gdf.copy()
    for col in gdf.columns:
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
    GeoJson(gdf).add_to(m)
    return m._repr_html_()

# Layout
dash_app.layout = dbc.Container([
    html.H2("Tiled OSM Downloader with RAM Estimation"),

    dbc.Row([
        dbc.Col([
            html.Label("Location:"),
            dcc.Input(id='location-input', type='text', placeholder='e.g. Manhattan, New York, USA', debounce=True, style={'width': '100%'}),
            html.Br(), html.Br(),

            html.Label("Select tags:"),
            dcc.Dropdown(
                id='tag-dropdown',
                options=[{"label": tag, "value": tag} for tag in ["building", "highway", "landuse", "natural", "amenity", "leisure", "railway"]],
                value=["highway"],
                multi=True
            ),

            html.Br(),
            html.Div(id='estimation-output'),
            html.Div(id='confirm-section'),

            html.Br(),
            dbc.Button("Download Tiles", id="download-btn", color="primary", className="mt-2", n_clicks=0),
            html.Div(id="download-status", className="mt-2")
        ], width=4),

        dbc.Col([
            html.Iframe(id="map", srcDoc=None, width="100%", height="600")
        ], width=8)
    ])
], fluid=True)

# State vars
session = {
    "tiles": [],
    "tags": {},
    "bounds": (),
    "gdf": None
}

# Callbacks
@dash_app.callback(
    Output("estimation-output", "children"),
    Input("location-input", "value"),
    Input("tag-dropdown", "value")
)
def estimate_ram(location, tags):
    if not location or not tags:
        raise PreventUpdate
    try:
        bounds_array = ox.geocode_to_gdf(location).total_bounds
        west, south, east, north = bounds_array
        session["bounds"] = (north, south, east, west)
        session["tags"] = {tag: True for tag in tags}
        tiles = get_tiles(session["bounds"], TILE_SIZE_DEG)
        session["tiles"] = tiles[:MAX_TILES_HARD_LIMIT]
        sample_ram_list = fetch_sample_tiles(session["tags"], session["bounds"], TILE_SIZE_DEG, SAMPLE_TILE_COUNT)
        avg_sample_ram_mb = sum(sample_ram_list) / len(sample_ram_list)
        estimated_ram = avg_sample_ram_mb * len(session["tiles"]) * RAM_SAFETY_FACTOR
        return html.Div([
            html.Div(f"Total tiles: {len(session['tiles'])}"),
            html.Div(f"Estimated RAM usage: ~{estimated_ram:.2f} MB")
        ])
    except Exception as e:
        return html.Div(f"Error estimating: {e}", style={"color": "red"})

@dash_app.callback(
    Output("download-status", "children"),
    Output("map", "srcDoc"),
    Input("download-btn", "n_clicks")
)
def download_tiles(n_clicks):
    if n_clicks == 0:
        raise PreventUpdate
    try:
        all_gdfs = []
        for i, (n, s, e, w) in enumerate(session["tiles"]):
            gdf_tile = ox.features_from_bbox((w, s, e, n), session["tags"])
            if not gdf_tile.empty:
                all_gdfs.append(gdf_tile)
        if all_gdfs:
            gdf_full = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=all_gdfs[0].crs)
            session["gdf"] = gdf_full
            html_map = generate_map(gdf_full)
            return f"Downloaded {len(gdf_full)} features.", html_map
        return "No data downloaded.", None
    except Exception as e:
        return f"Download error: {e}", None

if __name__ == "__main__":
    dash_app.run_server(debug=True, port=8050)
