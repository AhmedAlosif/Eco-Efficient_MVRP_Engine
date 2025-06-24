import streamlit as st
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

st.set_page_config(page_title="SmartDispatch Dashboard", layout="wide")

# Titles and Text

st.title("Main Title")
st.header("Header")
st.subheader("Subheader")
st.markdown("**Markdown** text here.")
st.text("Plain text")

# Sidebar

st.sidebar.title("Scenario Designer")
vehicle_type = st.sidebar.selectbox("Vehicle Type", ["Truck", "Bike", "Van"])
fleet_size = st.sidebar.slider("Number of vehicles", 1, 50, 10)
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

st.text_input("Enter text")
st.number_input("Enter number")
st.file_uploader("Upload File")

# Visuals

st.line_chart(map_data)
st.bar_chart(map_data)
st.map(map_data)
# or for folium:
# from streamlit_folium import folium_static
# folium_static(my_map)

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
