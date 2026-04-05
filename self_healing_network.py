"""
Self-Healing Network Connectivity Using BFS-DSU Hybrid Recovery
================================================================
Advanced Graph Theory — Digital Assignment II

This module implements a complete self-healing network simulation framework:
  - Graph generation (Watts-Strogatz, Barabási-Albert, Erdős-Rényi, Grid)
  - Locality-aware dormant edge pools
  - Multiple failure modes (random, targeted, cascading)
  - BFS-based partition detection
  - Kruskal-DSU hybrid healing algorithm
  - Baseline healers for comparison (random, degree-based)
  - Comprehensive metrics computation

Author : Fang
Date   : April 2026
"""

import networkx as nx
import numpy as np
import random
import math
import time
from collections import deque
from copy import deepcopy


# ============================================================================
# 1. DISJOINT SET UNION (DSU)
# ============================================================================

class DSU:
    """
    Disjoint Set Union (Union-Find) with Path Compression and Union by Rank.
    
    This data structure efficiently tracks connected components and supports
    near-O(1) amortized union and find operations via:
      - Path compression: flattens tree during find()
      - Union by rank: attaches shorter tree under taller tree
    
    Time Complexity:  O(α(n)) per operation (inverse Ackermann — effectively constant)
    Space Complexity: O(n)
    """

    def __init__(self, nodes):
        """Initialize DSU with each node as its own component."""
        self.parent = {n: n for n in nodes}
        self.rank = {n: 0 for n in nodes}
        self.component_count = len(self.parent)

    def find(self, i):
        """Find root representative with path compression."""
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        """
        Merge components containing i and j using union by rank.
        
        Returns:
            bool: True if merge happened, False if already in same component.
        """
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i == root_j:
            return False

        # Union by rank
        if self.rank[root_i] < self.rank[root_j]:
            self.parent[root_i] = root_j
        elif self.rank[root_i] > self.rank[root_j]:
            self.parent[root_j] = root_i
        else:
            self.parent[root_j] = root_i
            self.rank[root_i] += 1

        self.component_count -= 1
        return True

    def connected(self, i, j):
        """Check if i and j are in the same component."""
        return self.find(i) == self.find(j)

    def get_components(self):
        """Return dict mapping root → set of nodes in that component."""
        comps = {}
        for node in self.parent:
            root = self.find(node)
            comps.setdefault(root, set()).add(node)
        return comps


# ============================================================================
# 2. GRAPH GENERATORS
# ============================================================================

def generate_graph(topology, n, seed=42, **kwargs):
    """
    Generate a graph of the specified topology.
    
    Args:
        topology: One of 'watts_strogatz', 'barabasi_albert', 'erdos_renyi', 'grid'
        n: Number of nodes (for grid, creates ceil(sqrt(n)) x ceil(sqrt(n)))
        seed: Random seed for reproducibility
        **kwargs: Additional topology-specific parameters
    
    Returns:
        G: NetworkX graph
        pos: Node position dict for visualization
    """
    if topology == 'watts_strogatz':
        k = kwargs.get('k', 4)
        p = kwargs.get('p', 0.1)
        G = nx.watts_strogatz_graph(n=n, k=k, p=p, seed=seed)
        pos = nx.spring_layout(G, seed=seed)

    elif topology == 'barabasi_albert':
        m = kwargs.get('m', 2)
        G = nx.barabasi_albert_graph(n=n, m=m, seed=seed)
        pos = nx.spring_layout(G, seed=seed)

    elif topology == 'erdos_renyi':
        p = kwargs.get('p', 0.08)
        # Ensure connectivity by retrying with higher p if needed
        for attempt in range(10):
            G = nx.erdos_renyi_graph(n=n, p=p + attempt * 0.02, seed=seed + attempt)
            if nx.is_connected(G):
                break
        pos = nx.spring_layout(G, seed=seed)

    elif topology == 'grid':
        side = int(math.ceil(math.sqrt(n)))
        G = nx.grid_2d_graph(side, side)
        # Relabel to integer nodes
        mapping = {node: i for i, node in enumerate(G.nodes())}
        G = nx.relabel_nodes(G, mapping)
        # Keep only n nodes
        if len(G.nodes()) > n:
            remove = list(G.nodes())[n:]
            G.remove_nodes_from(remove)
        pos = {i: (i % side, i // side) for i in G.nodes()}

    else:
        raise ValueError(f"Unknown topology: {topology}")

    return G, pos


# ============================================================================
# 3. DORMANT EDGE GENERATOR
# ============================================================================

def generate_dormant_edges(G, pos, budget_ratio=0.30, locality_bias=True, seed=42):
    """
    Generate a pool of dormant (backup) edges not present in the active graph.
    
    Innovation: Locality-Aware edge generation preferentially creates backup
    links between geographically close nodes, simulating realistic constraints
    (e.g., shorter cable runs, stronger wireless signals).
    
    Args:
        G: The active graph
        pos: Node position dict
        budget_ratio: Fraction of active edges to create as dormant (default 30%)
        locality_bias: If True, prefer shorter edges (innovation extension)
        seed: Random seed
    
    Returns:
        dormant_edges: List of (u, v, {'weight': w}) tuples sorted by weight
    """
    rng = random.Random(seed)
    nodes = list(G.nodes())
    num_dormant = max(int(len(G.edges()) * budget_ratio), 5)

    # Generate all possible non-existing edges with their geometric weights
    candidates = []
    for i, u in enumerate(nodes):
        for v in nodes[i + 1:]:
            if not G.has_edge(u, v):
                dist = math.hypot(pos[u][0] - pos[v][0], pos[u][1] - pos[v][1])
                weight = round(dist * 100, 2)
                candidates.append((u, v, weight))

    if locality_bias:
        # Sort by distance — prefer closer edges
        candidates.sort(key=lambda x: x[2])
        # Take the closest ones with some randomness
        top_pool = candidates[:min(len(candidates), num_dormant * 3)]
        rng.shuffle(top_pool)
        selected = top_pool[:num_dormant]
    else:
        rng.shuffle(candidates)
        selected = candidates[:num_dormant]

    dormant_edges = [(u, v, {'weight': w}) for u, v, w in selected]
    # Sort by weight for Kruskal's algorithm
    dormant_edges.sort(key=lambda x: x[2]['weight'])
    return dormant_edges


# ============================================================================
# 4. FAILURE SIMULATOR
# ============================================================================

def simulate_failure(G, mode='random', failure_rate=0.15, seed=42):
    """
    Simulate node failures on the graph.
    
    Failure Modes:
        - 'random': Uniformly random node removal
        - 'targeted': Remove highest-degree nodes first (models deliberate attacks)
        - 'cascading': Multi-round failures where neighbors of failed nodes
                       have increased failure probability (innovation extension)
    
    Args:
        G: Input graph
        mode: 'random', 'targeted', or 'cascading'
        failure_rate: Fraction of nodes to fail
        seed: Random seed
    
    Returns:
        G_failed: Graph after node removal
        failed_nodes: List of removed nodes
    """
    rng = random.Random(seed)
    nodes = list(G.nodes())
    n = len(nodes)
    num_failures = max(int(n * failure_rate), 1)

    if mode == 'random':
        failed_nodes = rng.sample(nodes, min(num_failures, len(nodes)))

    elif mode == 'targeted':
        # Attack highest-degree nodes first (worst-case scenario)
        degree_sorted = sorted(nodes, key=lambda x: G.degree(x), reverse=True)
        failed_nodes = degree_sorted[:num_failures]

    elif mode == 'cascading':
        # Round 1: Random initial failures
        initial_fails = max(num_failures // 3, 1)
        failed_nodes = set(rng.sample(nodes, min(initial_fails, len(nodes))))

        # Round 2+: Neighbors of failed nodes have 30% chance of failing
        remaining_budget = num_failures - len(failed_nodes)
        cascade_prob = 0.30
        for _ in range(3):  # Max 3 cascade rounds
            if remaining_budget <= 0:
                break
            at_risk = set()
            for fn in failed_nodes:
                for neighbor in G.neighbors(fn):
                    if neighbor not in failed_nodes:
                        at_risk.add(neighbor)
            for node in at_risk:
                if remaining_budget <= 0:
                    break
                if rng.random() < cascade_prob:
                    failed_nodes.add(node)
                    remaining_budget -= 1

        failed_nodes = list(failed_nodes)
    else:
        raise ValueError(f"Unknown failure mode: {mode}")

    G_failed = G.copy()
    G_failed.remove_nodes_from(failed_nodes)
    return G_failed, failed_nodes


# ============================================================================
# 5. BFS PARTITION DETECTOR
# ============================================================================

def detect_partitions_bfs(G):
    """
    Detect disconnected components using BFS traversal.
    
    This implements the Detection phase of the BFS-DSU Hybrid:
    starting from an arbitrary node, BFS explores reachable nodes.
    If not all nodes are reached, a partition is flagged.
    
    Time Complexity:  O(V + E)
    Space Complexity: O(V)
    
    Args:
        G: Input graph
    
    Returns:
        components: List of sets, each containing nodes in one component
        is_connected: Boolean indicating if graph is still connected
        partition_detected: True if network is fragmented
    """
    if len(G.nodes()) == 0:
        return [], True, False

    visited = set()
    components = []
    nodes = list(G.nodes())

    for start in nodes:
        if start in visited:
            continue
        # BFS from this unvisited node
        component = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)

    is_connected = len(components) == 1
    partition_detected = not is_connected

    return components, is_connected, partition_detected


# ============================================================================
# 6. HEALING ALGORITHMS
# ============================================================================

def heal_kruskal_dsu(G_failed, dormant_edges):
    """
    Kruskal-DSU Hybrid Healing Algorithm (Primary — from DA-1 proposal).
    
    Two-phase approach:
      Phase 1: Initialize DSU with existing edges (components already known)
      Phase 2: Greedily activate minimum-weight dormant edges that bridge
               different components (Kruskal's logic)
    
    Innovation: Edges are weighted by geometric locality, so the algorithm
    naturally prefers shorter (lower latency/cost) backup links.
    
    Time Complexity:  O(E_dormant · log(E_dormant) + V · α(V))
    Space Complexity: O(V)
    
    Args:
        G_failed: Graph after failure
        dormant_edges: Sorted list of (u, v, {'weight': w}) candidate edges
    
    Returns:
        G_healed: Healed graph
        edges_added: List of (u, v) edges that were activated
        healing_steps: List of graph snapshots for animation
    """
    G_healed = G_failed.copy()
    surviving_nodes = set(G_healed.nodes())

    if len(surviving_nodes) == 0:
        return G_healed, [], [G_healed.copy()]

    # Phase 1: Build DSU from existing connectivity
    dsu = DSU(surviving_nodes)
    for u, v in G_healed.edges():
        dsu.union(u, v)

    # Phase 2: Filter dormant edges to only those connecting surviving nodes
    valid_dormant = [
        (u, v, d) for u, v, d in dormant_edges
        if u in surviving_nodes and v in surviving_nodes
    ]
    # Already sorted by weight (locality)

    edges_added = []
    healing_steps = [G_healed.copy()]

    for u, v, data in valid_dormant:
        if dsu.component_count <= 1:
            break  # Fully connected
        if dsu.union(u, v):
            G_healed.add_edge(u, v, **data)
            edges_added.append((u, v))
            healing_steps.append(G_healed.copy())

    return G_healed, edges_added, healing_steps


def heal_random(G_failed, dormant_edges, seed=42):
    """
    Baseline 1: Random Edge Activation.
    
    Randomly activates dormant edges without considering weight or locality.
    Used as a lower-bound baseline comparison.
    
    Args:
        G_failed: Graph after failure
        dormant_edges: List of candidate edges
        seed: Random seed
    
    Returns:
        G_healed, edges_added, healing_steps
    """
    rng = random.Random(seed)
    G_healed = G_failed.copy()
    surviving_nodes = set(G_healed.nodes())

    if len(surviving_nodes) == 0:
        return G_healed, [], [G_healed.copy()]

    dsu = DSU(surviving_nodes)
    for u, v in G_healed.edges():
        dsu.union(u, v)

    valid_dormant = [
        (u, v, d) for u, v, d in dormant_edges
        if u in surviving_nodes and v in surviving_nodes
    ]
    rng.shuffle(valid_dormant)  # Random order instead of sorted

    edges_added = []
    healing_steps = [G_healed.copy()]

    for u, v, data in valid_dormant:
        if dsu.component_count <= 1:
            break
        if dsu.union(u, v):
            G_healed.add_edge(u, v, **data)
            edges_added.append((u, v))
            healing_steps.append(G_healed.copy())

    return G_healed, edges_added, healing_steps


def heal_degree_based(G_failed, dormant_edges):
    """
    Baseline 2: Degree-Based Heuristic Healing.
    
    Prioritizes dormant edges connecting higher-degree nodes (hubs),
    under the heuristic that reconnecting hubs restores more paths.
    
    Args:
        G_failed: Graph after failure
        dormant_edges: List of candidate edges
    
    Returns:
        G_healed, edges_added, healing_steps
    """
    G_healed = G_failed.copy()
    surviving_nodes = set(G_healed.nodes())

    if len(surviving_nodes) == 0:
        return G_healed, [], [G_healed.copy()]

    dsu = DSU(surviving_nodes)
    for u, v in G_healed.edges():
        dsu.union(u, v)

    valid_dormant = [
        (u, v, d) for u, v, d in dormant_edges
        if u in surviving_nodes and v in surviving_nodes
    ]
    # Sort by sum of degrees (descending) — prefer hub connections
    degrees = dict(G_healed.degree())
    valid_dormant.sort(
        key=lambda x: degrees.get(x[0], 0) + degrees.get(x[1], 0),
        reverse=True
    )

    edges_added = []
    healing_steps = [G_healed.copy()]

    for u, v, data in valid_dormant:
        if dsu.component_count <= 1:
            break
        if dsu.union(u, v):
            G_healed.add_edge(u, v, **data)
            edges_added.append((u, v))
            healing_steps.append(G_healed.copy())

    return G_healed, edges_added, healing_steps


# ============================================================================
# 7. ADAPTIVE DORMANT POOL (Innovation Extension)
# ============================================================================

def generate_adaptive_dormant(G_failed, pos, budget=10, seed=42):
    """
    Innovation Extension: Adaptive Dormant Edge Pool.
    
    Instead of a static pre-generated pool, this generates backup edges
    dynamically near failure zones. Simulates emergency link provisioning
    (e.g., deploying temporary wireless bridges near damaged areas).
    
    Args:
        G_failed: Graph after failure
        pos: Node position dict
        budget: Maximum new edges to generate
        seed: Random seed
    
    Returns:
        adaptive_edges: List of (u, v, {'weight': w}) tuples
    """
    rng = random.Random(seed)
    components, is_connected, _ = detect_partitions_bfs(G_failed)

    if is_connected or len(components) < 2:
        return []

    adaptive_edges = []
    # For each pair of components, find the closest node pair
    for i in range(len(components)):
        for j in range(i + 1, len(components)):
            best_dist = float('inf')
            best_pair = None
            for u in components[i]:
                for v in components[j]:
                    if u in pos and v in pos:
                        dist = math.hypot(
                            pos[u][0] - pos[v][0],
                            pos[u][1] - pos[v][1]
                        )
                        if dist < best_dist:
                            best_dist = dist
                            best_pair = (u, v)
            if best_pair and len(adaptive_edges) < budget:
                weight = round(best_dist * 100, 2)
                adaptive_edges.append(
                    (best_pair[0], best_pair[1], {'weight': weight})
                )

    adaptive_edges.sort(key=lambda x: x[2]['weight'])
    return adaptive_edges


# ============================================================================
# 8. METRICS CALCULATOR
# ============================================================================

def compute_metrics(G_initial, G_failed, G_healed, failed_nodes, edges_added):
    """
    Compute comprehensive network metrics for analysis.
    
    Args:
        G_initial: Original graph before failure
        G_failed: Graph after failure
        G_healed: Graph after healing
        failed_nodes: List of failed nodes
        edges_added: List of edges activated during healing
    
    Returns:
        dict: Dictionary of computed metrics
    """
    metrics = {}

    # Basic counts
    metrics['initial_nodes'] = G_initial.number_of_nodes()
    metrics['initial_edges'] = G_initial.number_of_edges()
    metrics['nodes_failed'] = len(failed_nodes)
    metrics['failure_rate'] = len(failed_nodes) / G_initial.number_of_nodes()
    metrics['surviving_nodes'] = G_failed.number_of_nodes()
    metrics['surviving_edges'] = G_failed.number_of_edges()

    # Component analysis
    comps_failed = list(nx.connected_components(G_failed))
    metrics['components_after_failure'] = len(comps_failed)
    metrics['largest_component_failed'] = max(len(c) for c in comps_failed) if comps_failed else 0

    comps_healed = list(nx.connected_components(G_healed))
    metrics['components_after_healing'] = len(comps_healed)
    metrics['largest_component_healed'] = max(len(c) for c in comps_healed) if comps_healed else 0

    # Healing effectiveness
    metrics['edges_activated'] = len(edges_added)
    metrics['is_fully_healed'] = nx.is_connected(G_healed) if G_healed.number_of_nodes() > 0 else False
    metrics['healing_ratio'] = (
        (metrics['components_after_failure'] - metrics['components_after_healing'])
        / max(metrics['components_after_failure'] - 1, 1)
    ) if metrics['components_after_failure'] > 1 else 1.0

    # Total healing edge weight (cost)
    total_weight = sum(
        G_healed[u][v].get('weight', 0) for u, v in edges_added
        if G_healed.has_edge(u, v)
    )
    metrics['total_healing_cost'] = round(total_weight, 2)
    metrics['avg_edge_cost'] = round(total_weight / max(len(edges_added), 1), 2)

    # Graph properties (on largest component for disconnected graphs)
    if G_healed.number_of_nodes() > 0 and nx.is_connected(G_healed):
        metrics['diameter_healed'] = nx.diameter(G_healed)
        metrics['avg_path_length_healed'] = round(
            nx.average_shortest_path_length(G_healed), 3
        )
    else:
        # Compute on largest component
        if comps_healed:
            largest = max(comps_healed, key=len)
            sg = G_healed.subgraph(largest)
            if len(largest) > 1:
                metrics['diameter_healed'] = nx.diameter(sg)
                metrics['avg_path_length_healed'] = round(
                    nx.average_shortest_path_length(sg), 3
                )
            else:
                metrics['diameter_healed'] = 0
                metrics['avg_path_length_healed'] = 0
        else:
            metrics['diameter_healed'] = 0
            metrics['avg_path_length_healed'] = 0

    # Initial graph properties for comparison
    if nx.is_connected(G_initial):
        metrics['diameter_initial'] = nx.diameter(G_initial)
        metrics['avg_path_length_initial'] = round(
            nx.average_shortest_path_length(G_initial), 3
        )
    else:
        metrics['diameter_initial'] = -1
        metrics['avg_path_length_initial'] = -1

    # Clustering coefficient comparison
    metrics['clustering_initial'] = round(nx.average_clustering(G_initial), 4)
    metrics['clustering_healed'] = round(nx.average_clustering(G_healed), 4)

    return metrics


def compute_metrics_quick(G_failed, G_healed, edges_added):
    """
    Compute lightweight metrics for batch experiments (faster).
    
    Returns:
        dict with key metrics only
    """
    metrics = {}
    comps_failed = nx.number_connected_components(G_failed)
    comps_healed = nx.number_connected_components(G_healed)

    metrics['components_after_failure'] = comps_failed
    metrics['components_after_healing'] = comps_healed
    metrics['edges_activated'] = len(edges_added)
    metrics['is_fully_healed'] = nx.is_connected(G_healed) if G_healed.number_of_nodes() > 0 else False
    metrics['healing_ratio'] = (
        (comps_failed - comps_healed) / max(comps_failed - 1, 1)
    ) if comps_failed > 1 else 1.0

    total_weight = sum(
        G_healed[u][v].get('weight', 0) for u, v in edges_added
        if G_healed.has_edge(u, v)
    )
    metrics['total_healing_cost'] = round(total_weight, 2)

    return metrics


# ============================================================================
# 9. SINGLE SIMULATION RUNNER
# ============================================================================

def run_simulation(topology='watts_strogatz', n=50, failure_rate=0.15,
                   failure_mode='random', healer='kruskal_dsu',
                   dormant_budget=0.30, seed=42, verbose=True):
    """
    Run a complete self-healing simulation pipeline.
    
    Args:
        topology: Graph type ('watts_strogatz', 'barabasi_albert', 'erdos_renyi', 'grid')
        n: Number of nodes
        failure_rate: Fraction of nodes to fail
        failure_mode: 'random', 'targeted', or 'cascading'
        healer: 'kruskal_dsu', 'random', or 'degree_based'
        dormant_budget: Fraction of edges for dormant pool
        seed: Random seed
        verbose: Print results
    
    Returns:
        dict with all simulation data and metrics
    """
    # Step 1: Generate graph
    G, pos = generate_graph(topology, n, seed=seed)

    # Step 2: Generate dormant edges
    dormant = generate_dormant_edges(G, pos, budget_ratio=dormant_budget, seed=seed)

    # Step 3: Simulate failure
    G_failed, failed_nodes = simulate_failure(G, mode=failure_mode,
                                               failure_rate=failure_rate, seed=seed)

    # Step 4: Detect partitions
    components, is_connected, partition_detected = detect_partitions_bfs(G_failed)

    # Step 5: Heal
    start_time = time.time()
    if healer == 'kruskal_dsu':
        G_healed, edges_added, healing_steps = heal_kruskal_dsu(G_failed, dormant)
    elif healer == 'random':
        G_healed, edges_added, healing_steps = heal_random(G_failed, dormant, seed=seed)
    elif healer == 'degree_based':
        G_healed, edges_added, healing_steps = heal_degree_based(G_failed, dormant)
    else:
        raise ValueError(f"Unknown healer: {healer}")
    heal_time = time.time() - start_time

    # Step 6: Compute metrics
    metrics = compute_metrics(G, G_failed, G_healed, failed_nodes, edges_added)
    metrics['heal_time_ms'] = round(heal_time * 1000, 3)
    metrics['topology'] = topology
    metrics['healer'] = healer
    metrics['failure_mode'] = failure_mode

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Simulation: {topology} | n={n} | fail={failure_rate*100:.0f}% "
              f"({failure_mode}) | healer={healer}")
        print(f"{'='*60}")
        print(f"  Nodes failed        : {metrics['nodes_failed']}")
        print(f"  Components (failed) : {metrics['components_after_failure']}")
        print(f"  Components (healed) : {metrics['components_after_healing']}")
        print(f"  Edges activated     : {metrics['edges_activated']}")
        print(f"  Fully healed?       : {metrics['is_fully_healed']}")
        print(f"  Healing ratio       : {metrics['healing_ratio']:.2%}")
        print(f"  Total healing cost  : {metrics['total_healing_cost']}")
        print(f"  Heal time           : {metrics['heal_time_ms']:.3f} ms")
        print(f"{'='*60}")

    return {
        'G_initial': G,
        'G_failed': G_failed,
        'G_healed': G_healed,
        'pos': pos,
        'failed_nodes': failed_nodes,
        'edges_added': edges_added,
        'healing_steps': healing_steps,
        'dormant_edges': dormant,
        'metrics': metrics,
    }


# ============================================================================
# 10. MAIN — SINGLE DEMO RUN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  Self-Healing Network Connectivity — Demo Run")
    print("=" * 60)

    result = run_simulation(
        topology='watts_strogatz',
        n=50,
        failure_rate=0.15,
        failure_mode='random',
        healer='kruskal_dsu',
        dormant_budget=0.30,
        seed=42,
        verbose=True
    )

    # Verify DSU correctness
    print("\n--- DSU Unit Tests ---")
    dsu_test = DSU([1, 2, 3, 4, 5])
    assert dsu_test.find(1) == 1
    dsu_test.union(1, 2)
    assert dsu_test.connected(1, 2)
    assert not dsu_test.connected(1, 3)
    dsu_test.union(3, 4)
    dsu_test.union(2, 3)
    assert dsu_test.connected(1, 4)
    assert dsu_test.component_count == 2  # {1,2,3,4} and {5}
    print("  All DSU tests passed ✓")

    # Verify BFS detection
    print("\n--- BFS Partition Detection Test ---")
    comps, is_conn, part = detect_partitions_bfs(result['G_failed'])
    print(f"  Components detected: {len(comps)}")
    print(f"  Partition flagged:   {part}")
    assert len(comps) == result['metrics']['components_after_failure']
    print("  BFS detection test passed ✓")

    print(f"\nFull metrics: {result['metrics']}")
