import streamlit as st
import osmnx
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
import pandas as pd

map_data = pd.DataFrame({
    'lat': [24.7136, 24.7200, 24.7300],
    'lon': [46.6753, 46.6800, 46.6900]
})

result = {
    "cost": 3200,
    "co2": 240,
    "distance": 345,
    "delivery_times": [...],
    "vehicle_utilization": {...},
    "delayed_deliveries": 3
}

#  Page Configuration

st.set_page_config(page_title="MVRP Engine", layout="wide")

# Titles and Text

st.title("Main Title")
st.header("Header")
st.subheader("Subheader")
st.markdown("**Markdown** text here.")
st.text("Plain text")

# Sidebar

st.sidebar.title("Scenario Designer")
vehicle_type = st.sidebar.selectbox("Vehicle Type", ["Truck", "Bike", "Van"])
fleet_size = st.sidebar.text_input("Number of vehicles")
add_location = st.sidebar.text_input("New delivery point (lat,lon)")
delivery_deadline = st.sidebar.time_input("Latest delivery time")
st.sidebar.button("Run")

# Layouts

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Cost", f"${result['cost']}")
with col2:
    st.metric("CO₂ Emissions", f"{result['co2']} kg")

# Inputs

location_name = st.text_input("Enter location name (e.g., 'Manhattan, New York, USA')", key="location_input")
if location_name:
    try:
        ## Automatic method for getting 1km sample from the center
        place_gdf = osmnx.geocode_to_gdf(location_name) # Polygon of the location
        # Get center point of the polygon
        center = place_gdf.geometry.centroid.iloc[0]
        lat, lon = center.y, center.x
        # Define ~1 km² bounding box around center
        buffer_deg = 0.0045  # approx ~500 meters in lat/lon
        north = lat + buffer_deg
        south = lat - buffer_deg
        east = lon + buffer_deg
        west = lon - buffer_deg
        bbox = (north, south, east, west)
        # bbox for 1km sample
        tags = {"highway": True}  # you can change this to 'highway', 'landuse', etc.
        sample_gdf = osmnx.features_from_bbox(bbox, tags=tags)
        # Estimate RAM
        area_km2 = place_gdf.to_crs(place_gdf.estimate_utm_crs()).geometry.area.iloc[0] / 1e6
        sample_mb = sample_gdf.memory_usage(deep=True).sum() / (1024 ** 2)
        sample_area_km2 = 1  # number of samples (for increase accuracy)
        # Estimate RAM per km²
        ram_per_km2 = sample_mb / sample_area_km2
        estimated_ram = ram_per_km2 * area_km2
        # Step 2: Prompt the user about ram usage
        answer = st.radio(f"Current input will take {estimated_ram:.4f}MB of Ram, Do you want to continue?" , ("Yes", "No"))
        if answer == "Yes":
            # Step 3: Download features from OpenStreetMap
            tags = {"highway": True}  # you can change this to 'highway', 'landuse', etc.
            gdf = osmnx.features.features_from_place(location_name, tags=tags)
            # Step 4: Check features availablity
            if gdf.empty:
                st.warning("No features found for the selected tag in this location.")
            else:
                # Step 5: Create a Folium map centered on the data
                center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]
                m = folium.Map(location=center, zoom_start=13)
                # Step 6: Add GeoDataFrame to map
                folium.GeoJson(gdf).add_to(m)
                # Step 7: Show map in Streamlit
                st_folium(m, width=700, height=500)
        elif answer == "No":
            st.session_state["location_input"] = ""
    except Exception as e:
        st.error(f"Error: {e}")
        
st.number_input("Enter number")
st.file_uploader("Import Map file (.geojson)")

# Visuals

st.line_chart(map_data)
st.bar_chart(map_data)
#st.map(map_data)

#### Visualization example using folium (from smartmobilityalgorithms github)
# file downloaded from https://data.ontario.ca/dataset/ontario-s-health-region-geographic-data
# local file implementation
ontario = gpd.read_file('tests/Ontario_Health_Regions.shp')
ontario = ontario[(ontario.REGION != "North")]
ontario = ontario.to_crs(epsg=4326)

# Set starting location, initial zoom, and base layer source.
m = folium.Map(location=[43.67621,-79.40530],zoom_start=6, tiles='cartodbpositron')

for index, row in ontario.iterrows():
    # Simplify each region's polygon as intricate details are unnecessary
    sim_geo = gpd.GeoSeries(row['geometry']).simplify(tolerance=0.001)
    geo_j = sim_geo.to_json()
    geo_j = folium.GeoJson(data=geo_j, name=row['REGION'],style_function=lambda x: {'fillColor': 'black'})
    folium.Popup(row['REGION']).add_to(geo_j)
    geo_j.add_to(m)
####
# Add the draw plugin to the map
draw = Draw(export=True)
draw.add_to(m)
####
# Folium interactive map
st_folium(m)
####

# Expander & Tabs

with st.expander("More Info"):
    st.write("Expanded content")

tab1, tab2 = st.tabs(["Tab 1", "Tab 2"])
with tab1:
    st.write("Inside Tab 1")
with tab2:
    st.write("Inside Tab 2")

# Placeholders

placeholder = st.empty()
placeholder.write("Initial value")

# Caching

@st.cache_data
def load_data():
    return ...

# Buttons and Callbacks

if st.button("Run Optimizer"):
    st.success("Optimizer executed")

# Displaying Data

st.table(map_data)
st.dataframe(map_data)
st.json(map_data)