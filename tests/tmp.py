import geopandas as gpd # loading local files, 
import osmnx #
import DEAP #
import streamlit # dashboard
import networks # 
import json # for reading json files
import folium # for interactive map
from ortools.constraint_solver import pywrapcp, routing_enums_pb2 # or-tools solver


# file downloaded from https://data.ontario.ca/dataset/ontario-s-health-region-geographic-data
# local file implementation
ontario = gpd.read_file(r"../../data/ontario_health_regions/Ontario_Health_Regions.shp")
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

m
####

# loading street network from OSM (openstreetmap)
place = "Manhattan, New York, USA"
G = ox.graph_from_place(place, network_type='drive')

####
# Example of using DEAP for vrp
from deap import base, creator, tools, algorithms
import random

# Define problem, fitness, individuals (permutation for VRP)
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Example: Create a permutation individual for VRP with 10 nodes
toolbox.register("indices", random.sample, range(10), 10)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.indices)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Define crossover, mutation, and evaluation functions
# (You would implement VRP-specific evaluation of route costs here)

# Then run evolutionary algorithm or any custom metaheuristic
# function for creating vrp instances using or-tools

####
def create_vrp_data_model():
    """Stores the data for the problem."""
    data = {}
    # Distance matrix (depot + 4 customers)
    data["distance_matrix"] = [
        [0, 9, 8, 7, 14],   # depot
        [9, 0, 10, 15, 5],  # customer 1
        [8, 10, 0, 6, 11],  # customer 2
        [7, 15, 6, 0, 9],   # customer 3
        [14, 5, 11, 9, 0],  # customer 4
    ]
    data["num_vehicles"] = 2
    data["depot"] = 0
    data["demands"] = [0, 1, 1, 2, 4]  # depot has no demand
    data["vehicle_capacities"] = [5, 5]
    return data

#####
# function for solving vrp instance using or-tools
def solve_vrp():
    data = create_vrp_data_model()

    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["depot"]
    )

    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    routing.SetArcCostEvaluatorOfAllVehicles(distance_callback)

    # Add demand constraint
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        data["vehicle_capacities"],
        True,
        "Capacity"
    )

    # Setting first solution strategy
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    # Print solution
    if solution:
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            plan_output = f"Route for vehicle {vehicle_id}:\n"
            route_distance = 0
            route_load = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data["demands"][node_index]
                plan_output += f" {node_index} Load({route_load}) -> "
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            plan_output += f"{manager.IndexToNode(index)}\n"
            plan_output += f"Distance of the route: {route_distance}m\n"
            plan_output += f"Load of the route: {route_load}\n"
            print(plan_output)
    else:
        print("No solution found!")

solve_vrp()
#####

# Parse solomon benchmark files
def parse_solomon(file_path):
    with open(file_path) as f:
        lines = f.readlines()

    metadata = lines[0].strip()
    num_vehicles, vehicle_capacity = map(int, lines[4].split())

    customers = []
    for line in lines[9:]:
        if not line.strip():
            continue
        parts = list(map(float, line.strip().split()))
        customer_id = int(parts[0])
        x, y = parts[1], parts[2]
        demand = parts[3]
        ready_time = parts[4]
        due_date = parts[5]
        service_time = parts[6]
        customers.append({
            "id": customer_id,
            "x": x,
            "y": y,
            "demand": demand,
            "ready_time": ready_time,
            "due_date": due_date,
            "service_time": service_time
        })

    return num_vehicles, vehicle_capacity, customers
####

# Exmaple for using osmnx and networkx
import osmnx as ox
import networkx as nx

G = ox.graph_from_place("City, Country", network_type='drive')
node1 = ox.distance.nearest_nodes(G, lon1, lat1)
node2 = ox.distance.nearest_nodes(G, lon2, lat2)
distance = nx.shortest_path_length(G, node1, node2, weight='length')
####

# Example of estimating co2 emissions 
import osmnx as ox
import networkx as nx
import pandas as pd

# Step 1: Download road network for a city or region
place = "Oslo, Norway"
G = ox.graph_from_place(place, network_type="drive")

# Step 2: Simplify graph and calculate edge lengths (in km)
G = ox.add_edge_lengths(G)
edges = ox.graph_to_gdfs(G, nodes=False)
edges['length_km'] = edges['length'] / 1000  # convert meters to kilometers

# Step 3: Define vehicle fleet composition (total must = 1.0)
fleet_composition = {
    'passenger_car_petrol': 0.6,
    'passenger_car_diesel': 0.3,
    'light_commercial_diesel': 0.1
}

# Step 4: Define emission factors (g CO2 per km) from EMEP/EEA or HBEFA
emission_factors = {
    'passenger_car_petrol': 180.0,      # g/km
    'passenger_car_diesel': 140.0,      # g/km
    'light_commercial_diesel': 230.0    # g/km
}

# Step 5: Estimate total CO2 emissions per edge segment
def estimate_emission(row):
    total_emission = 0.0  # in grams
    for vehicle_type, share in fleet_composition.items():
        ef = emission_factors.get(vehicle_type, 0)
        total_emission += row['length_km'] * ef * share
    return total_emission

edges['co2_g'] = edges.apply(estimate_emission, axis=1)
edges['co2_kg'] = edges['co2_g'] / 1000

# Show sample output
print(edges[['highway', 'length_km', 'co2_kg']].head())
####

# Example of estimating co2 emissions with traffic volumes, time of day effects
# And vehicle speed
import osmnx as ox
import pandas as pd
import numpy as np

# 1. Download road network (you can replace with your region)
place = "Oslo, Norway"
G = ox.graph_from_place(place, network_type="drive")
G = ox.add_edge_lengths(G)
edges = ox.graph_to_gdfs(G, nodes=False)
edges['length_km'] = edges['length'] / 1000

# 2. Add synthetic traffic volumes (you can replace with real values)
np.random.seed(42)
edges['traffic_volume'] = np.random.randint(100, 1500, size=len(edges))  # vehicles/day

# 3. Assume average speeds per road type (can be dynamic if you have better data)
speed_map = {
    'motorway': 100,
    'trunk': 80,
    'primary': 60,
    'secondary': 50,
    'tertiary': 40,
    'residential': 30
}
edges['speed_kph'] = edges['highway'].map(speed_map).fillna(40)

# 4. Emission factors (g CO2/km) vary by speed and vehicle type (simplified example)
def get_emission_factor(vehicle_type, speed):
    if vehicle_type == 'passenger_car_petrol':
        return 220 if speed < 30 else 180 if speed < 80 else 160
    elif vehicle_type == 'passenger_car_diesel':
        return 200 if speed < 30 else 140 if speed < 80 else 130
    elif vehicle_type == 'light_commercial_diesel':
        return 250 if speed < 30 else 230 if speed < 80 else 210
    return 0

# 5. Define vehicle fleet composition
fleet = {
    'passenger_car_petrol': 0.5,
    'passenger_car_diesel': 0.4,
    'light_commercial_diesel': 0.1
}

# 6. Compute emissions based on traffic volume and emission factors
def compute_edge_emissions(row):
    total_emissions = 0.0
    for vehicle, share in fleet.items():
        ef = get_emission_factor(vehicle, row['speed_kph'])  # g/km
        total_vehicle_km = row['length_km'] * row['traffic_volume'] * share
        total_emissions += total_vehicle_km * ef  # in grams
    return total_emissions

edges['co2_g'] = edges.apply(compute_edge_emissions, axis=1)
edges['co2_kg'] = edges['co2_g'] / 1000

# Optional: time of day effect (e.g., apply peak multiplier)
edges['peak_multiplier'] = 1.2  # synthetic
edges['co2_kg_peak'] = edges['co2_kg'] * edges['peak_multiplier']

# Show sample result
print(edges[['highway', 'length_km', 'traffic_volume', 'speed_kph', 
             'co2_kg', 'co2_kg_peak']].head())
####

# Example of getting centroid using geopandas
import osmnx as ox

gdf = ox.geometries_from_place("Berlin", tags={"building": True})
gdf_proj = gdf.to_crs("EPSG:54034")
gdf_proj['centroid'] = gdf_proj.centroid
####

# example code for fleet
fleet = [
    {
        "id": "vehicle_1",
        "capacity": 100,
        "start_location": (52.52, 13.405),  # Berlin (lat, lon)
        "end_location": (52.52, 13.405),
        "max_distance_km": 200
    },
    {
        "id": "vehicle_2",
        "capacity": 80,
        "start_location": (52.52, 13.405),
        "end_location": (52.52, 13.405),
        "max_distance_km": 150
    }
]
# or
fleet = [
    {
        "id": "vehicle_1",
        "capacity": 100,
        "start_location": (52.52, 13.405),  # Berlin (lat, lon)
        "end_location": (52.52, 13.405),
        "max_distance_km": 200
    },
    {
        "id": "vehicle_2",
        "capacity": 80,
        "start_location": (52.52, 13.405),
        "end_location": (52.52, 13.405),
        "max_distance_km": 150
    }
]
####

#exmaple of importing json and yaml
# JSON
import json
with open('fleet.json') as f:
    data = json.load(f)

# YAML
import yaml
with open('fleet.yaml') as f:
    data = yaml.safe_load(f)
####

# Example of Custom GA for Deadheading with DEAP
import random
from deap import base, creator, tools, algorithms
import numpy as np

# Example data: distance matrix (including depot at index 0)
distance_matrix = np.array([
    [0, 2, 9, 10],
    [1, 0, 6, 4],
    [15, 7, 0, 8],
    [6, 3, 12, 0]
])

NUM_CUSTOMERS = 3
NUM_VEHICLES = 1  # For simplicity; extend to multiple later

DEPOT = 0

# Fitness function: total distance including deadheading
def eval_deadheading(individual):
    total_distance = 0
    route = [DEPOT] + individual + [DEPOT]  # start and end at depot
    for i in range(len(route) - 1):
        total_distance += distance_matrix[route[i]][route[i+1]]
    return (total_distance,)

# Setup DEAP
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))  # minimize total distance
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Individual: permutation of customer nodes
toolbox.register("indices", random.sample, range(1, NUM_CUSTOMERS+1), NUM_CUSTOMERS)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.indices)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

toolbox.register("evaluate", eval_deadheading)
toolbox.register("mate", tools.cxOrdered)
toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
toolbox.register("select", tools.selTournament, tournsize=3)

def main():
    random.seed(42)
    pop = toolbox.population(n=50)
    hof = tools.HallOfFame(1)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min)
    stats.register("avg", np.mean)

    pop, log = algorithms.eaSimple(pop, toolbox, cxpb=0.7, mutpb=0.2, ngen=40,
                                   stats=stats, halloffame=hof, verbose=True)

    print("Best individual is ", hof[0], "with total distance", hof[0].fitness.values[0])

if __name__ == "__main__":
    main()
####
