# The orginal code is from this chapter:
# https://smartmobilityalgorithms.github.io/book/content/LogisticsProblems/eco_routing.html
'''
    This function is refine of the Dijsktra algorithm. 
    Here, we will terminate the searching after reaching the destination.
'''
def Dijkstra_fine(G,origin,destination, criteria = 'Distance'):
    # convert map nodes into index from 0 to length(nodes) to simplify our algorithm 
    n = len(G.nodes)
    map_nodes = list(G.nodes)
    # initial defination of the distance list with infinity for all nodes and zero for source node
    dist = [math.inf] * n
    dist[map_nodes.index(origin)] = 0
    # mark all nodes as unvisited 
    visited = [False] * n
    parent  = [None] * n
    while sum(visited) <= n:
        # index of the node of the minimum dist with condition that it is not visited
        current_node = dist.index(min(dist[at] for at in range(len(dist)) if visited[at]==False))
        # here, we will  terminate the searching after reaching the the required destination 
        if current_node == map_nodes.index(destination) :
            break
        # iterate over all neighbors of the current node
        for child in nx.neighbors(G,map_nodes[current_node]):
            # get distance between currrent node and child node
            distance = dist[current_node] + func(G,map_nodes[current_node],child, criteria)
            # update minimum distance if the calculated distnace is less than previous distance
            if distance < dist[map_nodes.index(child)]:
                dist[map_nodes.index(child)] = distance
                parent[map_nodes.index(child)] = current_node
        visited[current_node] = True
        #print(str(sum(visited)/len(visited)*100)+'--'+str(current_node))

    # here we can define our path back from the destination   
    path = []            
    path.append(map_nodes.index(destination))
    while path[-1] != None:
        path.append(parent[path[-1]])
    path.pop()
    path.reverse()
    return [map_nodes[i] for i in path]

'''
    this function represent the cost function we will define 
'''
# here we can put our required cost function :
def func(G, node1, node2, criteria):
    if criteria =='Distance':
        distance = G[node1][node2][0]['length'] # length between the nodes
    elif criteria == 'Time':
        distance = G[node1][node2][0]['travel_time'] # time between the nodes
    return distance
class Node:
    # using __slots__ for optimization
    __slots__ = ['node', 'distance', 'parent', 'osmid', 'G']
    # constructor for each node
    def __init__(self ,graph , osmid, distance = 0, parent = None):
        # the dictionary of each node as in networkx graph --- still needed for internal usage
        self.node = graph[osmid]
        # the distance from the parent node --- edge length
        self.distance = distance
        # the parent node
        self.parent = parent
        # unique identifier for each node so we don't use the dictionary returned from osmnx
        self.osmid = osmid
        # the graph
        self.G = graph
    # returning all the nodes adjacent to the node
    #def expand(self):
    #     children = [Node(graph = self.G, osmid = child, distance = self.node[child][0]['length'], parent = self) \
    #                    for child in self.node]
    def expand(self, criteria):
        children = []
        for child in self.node:
            if criteria == 'Time':
                dist = self.node[child][0]['travel_time']
            elif criteria == 'Distance':
                dist = self.node[child][0]['length']
            elif criteria == 'Fuel':
                point1_h = elevation[self.osmid]
                point2_h = elevation[child]
                leng = self.node[child][0]['length']
                grad = np.max([(point2_h -point1_h) / leng * 100, 0])
                speed = self.node[child][0]['speed_kph'] * 0.277777778 * 3
                dist = Estimate_Co2_Model2(grad, speed, leng)
        
            Node_ = Node(graph = self.G, 
                         osmid = child,
                         distance = dist,
                         parent = self)
            children.append(Node_)
        return children 
    # returns the path from that node to the origin as a list and the length of that path
    def path(self):
        node = self
        path = []
        while node:
            path.append(node.osmid)
            node = node.parent
        return path[::-1]
    # the following two methods are for dictating how comparison works
    def __eq__(self, other):
        try:
            return self.osmid == other.osmid
        except:
            return self.osmid == other
    def __hash__(self):
        return hash(self.osmid)
def Dijkstra(G,origin,destination,criteria = 'Distance'):
    seen = set()         # for dealing with self loops
    shortest_dist = {osmid: math.inf for osmid in G.nodes()}
    unrelaxed_nodes = [Node(graph = G, osmid = osmid) for osmid in G.nodes()]

    shortest_dist[origin.osmid] = 0
    found = False

    while len(unrelaxed_nodes) > 0 and not found:
        node = min(unrelaxed_nodes, key = lambda node : shortest_dist[node.osmid])  
        # relaxing the node, so this node's value in shortest_dist
        # is the shortest distance between the origin and destination
        unrelaxed_nodes.remove(node)
        seen.add(node.osmid)  
        # if the destination node has been relaxed
        # then that is the route we want
        if node == destination:
            route = node.path()
            cost = shortest_dist[node.osmid]
            found = True
            continue
        # otherwise, let's relax edges of its neighbours
        for child in node.expand(criteria):
            # skip self-loops
            if child.osmid in seen: continue
            # this doesn't look pretty because Node is just an object
            # so retrieving it is a bit verbose -- if you have nicer 
            # way to do that, please open an issue
            child_obj = next((node for node in unrelaxed_nodes if node.osmid == child.osmid), None)
            child_obj.distance = child.distance
            distance = shortest_dist[node.osmid] + child.distance
            if distance < shortest_dist[child_obj.osmid]:
                shortest_dist[child_obj.osmid] = distance
                child_obj.parent = node
    return route
