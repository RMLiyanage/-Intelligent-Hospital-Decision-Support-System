"""
data_structures/graph.py
========================
Weighted graph for the MediRoute hospital network.

This module is the foundation for:
  - Module 1 (Route Optimization): geographic location graph
  - Module 3 (Network Analysis):   hospital facility graph

DATA STRUCTURE CHOICE: ADJACENCY LIST
--------------------------------------
The Sri Lankan hospital road network is a SPARSE GRAPH.
With ~32 location nodes and ~52 road connections:
  - Average degree ≈ 3-4 edges per node

For sparse graphs, adjacency list wins:
  ┌────────────────┬──────────────────┬──────────────────┐
  │ Operation      │ Adjacency List   │ Adjacency Matrix │
  ├────────────────┼──────────────────┼──────────────────┤
  │ Space          │ O(V+E) = O(84)   │ O(V²) = O(1024) │
  │ Get neighbours │ O(degree)        │ O(V)             │
  │ Edge exists    │ O(degree)        │ O(1)             │
  │ Add edge       │ O(1)             │ O(1)             │
  └────────────────┴──────────────────┴──────────────────┘

get_neighbours() is called for every node popped from the priority queue
in A* and Dijkstra — O(degree) is critical for performance.

ADJACENCY MATRIX VIEW
---------------------
Floyd-Warshall requires O(V²) random access: dist[i][j].
The graph provides to_adjacency_matrix() which converts the
adjacency list to a V×V matrix on demand.

INTERNAL STORAGE
----------------
_nodes    : dict[int, GraphNode]        — O(1) lookup by ID
_adj_list : dict[int, list[GraphEdge]] — O(1) to get a node's edge list
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


# ============================================================
# GraphNode
# ============================================================

@dataclass
class GraphNode:
    """
    A vertex in the hospital network graph.

    In Module 1: a geographic location (city, town, junction)
    In Module 3: a hospital, department, clinic, or lab

    Attributes
    ----------
    node_id   : Unique integer (matches database locations.id)
    name      : Human-readable label
    latitude  : GPS latitude (used by A* Euclidean heuristic)
    longitude : GPS longitude (used by A* Euclidean heuristic)
    data      : Extra attributes (hospital_id, type, capacity…)
    """
    node_id: int
    name: str
    latitude: float = 0.0
    longitude: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GraphNode) and self.node_id == other.node_id

    def __repr__(self) -> str:
        return f"GraphNode(id={self.node_id}, name='{self.name}')"

    def to_dict(self) -> Dict:
        return {
            'id': self.node_id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            **self.data,
        }


# ============================================================
# GraphEdge
# ============================================================

@dataclass
class GraphEdge:
    """
    A weighted directed edge in the hospital network graph.

    Attributes
    ----------
    from_id     : Source node ID
    to_id       : Destination node ID
    distance    : Road distance in km  ← PRIMARY EDGE WEIGHT
    travel_time : Estimated travel time in minutes
    traffic     : 'low' | 'medium' | 'high'
    """
    from_id: int
    to_id: int
    distance: float
    travel_time: float = 0.0
    traffic: str = 'low'

    # Traffic multipliers for effective travel time
    _TRAFFIC_MULT: Dict[str, float] = field(
        default_factory=lambda: {'low': 1.0, 'medium': 1.3, 'high': 1.8},
        repr=False
    )

    @property
    def weight(self) -> float:
        """Primary weight used by A* and Dijkstra (distance in km)."""
        return self.distance

    @property
    def effective_travel_time(self) -> float:
        """Travel time adjusted for traffic conditions."""
        mult = {'low': 1.0, 'medium': 1.3, 'high': 1.8}.get(self.traffic, 1.0)
        return self.travel_time * mult

    def to_dict(self) -> Dict:
        return {
            'from': self.from_id,
            'to': self.to_id,
            'distance': self.distance,
            'travel_time': self.travel_time,
            'traffic': self.traffic,
        }


# ============================================================
# Graph
# ============================================================

class Graph:
    """
    Weighted graph for the MediRoute hospital network.

    PRIMARY REPRESENTATION: Adjacency List
    ----------------------------------------
    _adj_list: dict[int, list[GraphEdge]]

    Example (3 nodes):
        _adj_list = {
            1: [GraphEdge(1, 2, 116.0, 150, 'medium'),
                GraphEdge(1, 3, 120.0, 90,  'low')],
            2: [GraphEdge(2, 1, 116.0, 150, 'medium')],
            3: [GraphEdge(3, 1, 120.0, 90,  'low')],
        }

    SECONDARY REPRESENTATION: Adjacency Matrix (on demand)
    -------------------------------------------------------
    Used ONLY by Floyd-Warshall algorithm (O(V³) time, O(V²) space).
    Generated lazily via to_adjacency_matrix().

    TIME COMPLEXITIES
    -----------------
    add_node          : O(1)
    add_edge          : O(1)
    get_neighbors     : O(1)   ← direct dict lookup
    has_node          : O(1)
    has_edge          : O(degree)
    to_adjacency_matrix: O(V + E)
    """

    INF: float = float('inf')

    def __init__(self, directed: bool = False) -> None:
        """
        Parameters
        ----------
        directed : If False (default), add_edge inserts both directions.
        """
        self._nodes: Dict[int, GraphNode] = {}
        self._adj_list: Dict[int, List[GraphEdge]] = {}
        self._directed: bool = directed
        self._edge_count: int = 0  # counts directed edges

    # -------------------------------------------------------- #
    # Node operations                                          #
    # -------------------------------------------------------- #

    def add_node(self, node_id: int, name: str,
                 latitude: float = 0.0, longitude: float = 0.0,
                 **data: Any) -> 'GraphNode':
        """
        Add a vertex to the graph.

        If node already exists, returns existing node unchanged.

        Parameters
        ----------
        node_id   : Unique integer ID (matches DB locations.id)
        name      : Human-readable name
        latitude  : GPS latitude for A* heuristic
        longitude : GPS longitude for A* heuristic
        **data    : Additional attributes (stored in node.data)

        Returns
        -------
        GraphNode : The created or existing node.

        Time: O(1)
        """
        if node_id not in self._nodes:
            node = GraphNode(node_id, name, latitude, longitude, data)
            self._nodes[node_id] = node
            self._adj_list[node_id] = []
        return self._nodes[node_id]

    def get_node(self, node_id: int) -> Optional[GraphNode]:
        """Return node by ID, or None. Time: O(1)."""
        return self._nodes.get(node_id)

    def has_node(self, node_id: int) -> bool:
        """Check node existence. Time: O(1)."""
        return node_id in self._nodes

    def get_all_nodes(self) -> List[GraphNode]:
        """Return all nodes. Time: O(V)."""
        return list(self._nodes.values())

    def node_ids(self) -> List[int]:
        """Return all node IDs sorted. Time: O(V log V)."""
        return sorted(self._nodes.keys())

    @property
    def node_count(self) -> int:
        """Number of vertices. Time: O(1)."""
        return len(self._nodes)

    # -------------------------------------------------------- #
    # Edge operations                                          #
    # -------------------------------------------------------- #

    def add_edge(self, from_id: int, to_id: int,
                 distance: float, travel_time: float = 0.0,
                 traffic: str = 'low') -> None:
        """
        Add a weighted edge to the graph.

        For undirected graphs (directed=False), adds edges in BOTH
        directions so get_neighbors() works from either endpoint.

        Parameters
        ----------
        from_id     : Source node ID (must already exist)
        to_id       : Destination node ID (must already exist)
        distance    : Distance in km (primary weight for A*/Dijkstra)
        travel_time : Estimated travel time in minutes
        traffic     : Traffic level ('low', 'medium', 'high')

        Raises
        ------
        ValueError : If either node does not exist.

        Time: O(1)
        """
        if from_id not in self._nodes:
            raise ValueError(
                f"Source node {from_id} not found. Call add_node() first."
            )
        if to_id not in self._nodes:
            raise ValueError(
                f"Destination node {to_id} not found. Call add_node() first."
            )

        fwd = GraphEdge(from_id, to_id, distance, travel_time, traffic)
        self._adj_list[from_id].append(fwd)
        self._edge_count += 1

        if not self._directed:
            rev = GraphEdge(to_id, from_id, distance, travel_time, traffic)
            self._adj_list[to_id].append(rev)
            self._edge_count += 1

    def get_neighbors(self, node_id: int) -> List[GraphEdge]:
        """
        Return all outgoing edges from node_id.

        Called by every iteration of A*, Dijkstra, BFS, DFS.
        Returns a reference — O(1) lookup, O(degree) iteration.
        """
        return self._adj_list.get(node_id, [])

    def get_neighbor_ids(self, node_id: int) -> List[int]:
        """
        Return neighbor IDs only (no weights).

        Used by BFS and DFS where edge weight is not needed.
        Time: O(degree)
        """
        return [e.to_id for e in self._adj_list.get(node_id, [])]

    def has_edge(self, from_id: int, to_id: int) -> bool:
        """Check if a direct edge from → to exists. Time: O(degree)."""
        return any(e.to_id == to_id for e in self._adj_list.get(from_id, []))

    def get_edge(self, from_id: int, to_id: int) -> Optional[GraphEdge]:
        """Get the edge object between two nodes. Time: O(degree)."""
        for edge in self._adj_list.get(from_id, []):
            if edge.to_id == to_id:
                return edge
        return None

    @property
    def edge_count(self) -> int:
        """
        Number of directed edges stored.
        For undirected graph, divide by 2 for undirected count.
        """
        return self._edge_count

    # -------------------------------------------------------- #
    # Adjacency Matrix (for Floyd-Warshall)                   #
    # -------------------------------------------------------- #

    def to_adjacency_matrix(
        self,
    ) -> Tuple[List[List[float]], Dict[int, int], Dict[int, int]]:
        """
        Convert adjacency list to a V×V distance matrix.

        Floyd-Warshall cannot operate on an adjacency list.
        It requires random access: dist[i][j] in O(1).

        Returns
        -------
        matrix       : list[list[float]]
                       V×V matrix where matrix[i][j] = distance from
                       node at index i to node at index j.
                       INF = no direct edge; 0 = diagonal.
        id_to_index  : dict[int, int]   node_id → matrix row/col index
        index_to_id  : dict[int, int]   matrix index → node_id

        Time:  O(V + E)
        Space: O(V²)  ← dominated by the matrix itself
        """
        node_ids = sorted(self._nodes.keys())
        n = len(node_ids)
        id_to_index: Dict[int, int] = {nid: i for i, nid in enumerate(node_ids)}
        index_to_id: Dict[int, int] = {i: nid for nid, i in id_to_index.items()}

        # Initialise: INF everywhere, 0 on diagonal
        matrix: List[List[float]] = [[self.INF] * n for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 0.0

        # Fill direct edges (keep minimum if duplicate edges exist)
        for from_id, edges in self._adj_list.items():
            i = id_to_index[from_id]
            for edge in edges:
                j = id_to_index[edge.to_id]
                if edge.distance < matrix[i][j]:
                    matrix[i][j] = edge.distance

        return matrix, id_to_index, index_to_id

    # -------------------------------------------------------- #
    # Serialisation                                            #
    # -------------------------------------------------------- #

    def to_dict(self) -> Dict:
        """
        Serialise graph to a JSON-compatible dict.
        Used by API responses and the frontend graph visualiser.
        """
        seen_edges = set()
        edges_out = []
        for edges in self._adj_list.values():
            for edge in edges:
                key = (min(edge.from_id, edge.to_id),
                       max(edge.from_id, edge.to_id))
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges_out.append(edge.to_dict())

        return {
            'nodes': [n.to_dict() for n in self._nodes.values()],
            'edges': edges_out,
            'node_count': self.node_count,
            'edge_count': len(edges_out),
            'directed': self._directed,
        }

    # -------------------------------------------------------- #
    # Factory methods                                          #
    # -------------------------------------------------------- #

    @classmethod
    def from_db_data(
        cls,
        locations: List[Dict],
        routes: List[Dict],
        directed: bool = False,
    ) -> 'Graph':
        """
        Build a Graph from database query results.

        Parameters
        ----------
        locations : list of dicts — keys: id, name, latitude, longitude
        routes    : list of dicts — keys: source_location_id,
                    destination_location_id, distance_km,
                    travel_time_min, traffic_level, is_bidirectional

        Used by route_service.py and network_service.py to build the
        Sri Lankan hospital road network from MySQL.
        """
        graph = cls(directed=directed)

        for loc in locations:
            graph.add_node(
                int(loc['id']),
                loc['name'],
                latitude=float(loc.get('latitude', 0)),
                longitude=float(loc.get('longitude', 0)),
            )

        for route in routes:
            try:
                src = int(route['source_location_id'])
                dst = int(route['destination_location_id'])
                dist = float(route['distance_km'])
                time_ = float(route.get('travel_time_min', 0))
                traffic = route.get('traffic_level', 'low')
                bidir = bool(route.get('is_bidirectional', True))

                if bidir:
                    # add_edge already handles both directions for undirected
                    graph.add_edge(src, dst, dist, time_, traffic)
                else:
                    # Directed graph: only add one direction
                    fwd = GraphEdge(src, dst, dist, time_, traffic)
                    graph._adj_list[src].append(fwd)
                    graph._edge_count += 1
            except (KeyError, ValueError):
                pass  # Skip invalid rows silently

        return graph

    @classmethod
    def generate_random(
        cls,
        num_nodes: int,
        edge_probability: float = 0.15,
        min_weight: float = 5.0,
        max_weight: float = 250.0,
        seed: int = 42,
    ) -> 'Graph':
        """
        Generate a random connected graph for performance experiments.

        Used by experiments/run_experiments.py to test algorithm
        scalability across input sizes (50, 250, 1000, 5000 nodes).

        Guarantees connectivity via a random spanning tree before
        adding extra edges with probability `edge_probability`.

        Parameters
        ----------
        num_nodes        : Number of vertices
        edge_probability : Probability of each possible edge existing
        min_weight       : Minimum edge weight (km)
        max_weight       : Maximum edge weight (km)
        seed             : Random seed for reproducibility

        Time:  O(V²) worst case (dense graphs)
        Space: O(V + E)
        """
        rng = random.Random(seed)
        graph = cls(directed=False)

        # Add nodes with random Sri Lanka–range coordinates
        for i in range(1, num_nodes + 1):
            graph.add_node(
                i, f"Node_{i}",
                latitude=rng.uniform(5.9, 9.9),
                longitude=rng.uniform(79.6, 81.9),
            )

        # Spanning tree — guarantees all nodes are reachable
        ids = list(range(1, num_nodes + 1))
        rng.shuffle(ids)
        for i in range(1, len(ids)):
            w = round(rng.uniform(min_weight, max_weight), 2)
            t = round(w * 1.2, 1)  # rough travel time
            graph.add_edge(ids[i - 1], ids[i], w, t)

        # Additional random edges
        for i in range(1, num_nodes + 1):
            for j in range(i + 1, num_nodes + 1):
                if rng.random() < edge_probability and not graph.has_edge(i, j):
                    w = round(rng.uniform(min_weight, max_weight), 2)
                    t = round(w * 1.2, 1)
                    graph.add_edge(i, j, w, t)

        return graph

    # -------------------------------------------------------- #
    # Display                                                  #
    # -------------------------------------------------------- #

    def print_adjacency_list(self) -> None:
        """Print the full adjacency list for debugging / report output."""
        undirected_edges = self._edge_count // (1 if self._directed else 2)
        print(f"\nAdjacency List  "
              f"({self.node_count} nodes, {undirected_edges} edges, "
              f"directed={self._directed})")
        print("─" * 70)
        for node_id in sorted(self._adj_list.keys()):
            node = self._nodes[node_id]
            edges = self._adj_list[node_id]
            neighbors = ", ".join(
                f"{self._nodes[e.to_id].name}({e.distance:.1f} km)"
                for e in edges
            )
            print(f"  {node.name:<28} → [{neighbors}]")

    def __repr__(self) -> str:
        undirected_edges = self._edge_count // (1 if self._directed else 2)
        return (
            f"Graph(nodes={self.node_count}, "
            f"edges={undirected_edges}, "
            f"directed={self._directed})"
        )
