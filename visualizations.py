"""
Visualization Module for Self-Healing Network Connectivity
============================================================
Advanced Graph Theory — Digital Assignment II

Generates publication-quality figures:
  - 3-panel: Initial → Failed → Healed network visualization
  - Step-by-step healing animation GIF
  - Network metrics comparison heatmap

Author : Fang
Date   : April 2026
"""

import os
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
import numpy as np

from self_healing_network import run_simulation, detect_partitions_bfs

OUTPUT_DIR = 'results'
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# 1. THREE-PANEL VISUALIZATION (Initial → Failed → Healed)
# ============================================================================

def plot_three_panel(result, filename='three_panel.png', title_suffix=''):
    """
    Generate the signature 3-panel network visualization.
    
    Panel 1: Initial network (all nodes active, dormant edges dashed)
    Panel 2: After failure (failed nodes red, components color-coded)
    Panel 3: After healing (healed edges highlighted green)
    """
    G_initial = result['G_initial']
    G_failed = result['G_failed']
    G_healed = result['G_healed']
    pos = result['pos']
    failed_nodes = result['failed_nodes']
    edges_added = result['edges_added']
    dormant_edges = result['dormant_edges']
    metrics = result['metrics']

    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    fig.suptitle(
        f"Self-Healing Network Connectivity{title_suffix}\n"
        f"[{metrics['topology'].replace('_', '-').title()} | "
        f"n={metrics['initial_nodes']} | "
        f"Failed: {metrics['nodes_failed']} ({metrics['failure_rate']*100:.0f}%)]",
        fontsize=15, fontweight='bold', y=1.02
    )

    # ── Panel 1: Initial Network ──
    ax = axes[0]
    nx.draw_networkx_nodes(G_initial, pos, ax=ax,
                           node_color='#64B5F6', node_size=120,
                           edgecolors='#1565C0', linewidths=0.8)
    nx.draw_networkx_edges(G_initial, pos, ax=ax,
                           edge_color='#90A4AE', width=1.0, alpha=0.7)
    # Draw dormant edges as dashed
    dormant_edge_list = [(u, v) for u, v, _ in dormant_edges
                         if G_initial.has_node(u) and G_initial.has_node(v)]
    if dormant_edge_list:
        nx.draw_networkx_edges(G_initial, pos, edgelist=dormant_edge_list,
                               edge_color='#B0BEC5', width=0.7, style='dashed',
                               alpha=0.4, ax=ax)
    ax.set_title(f"1. Initial Network\n({G_initial.number_of_nodes()} nodes, "
                 f"{G_initial.number_of_edges()} edges)", fontsize=12)
    ax.axis('off')

    # Legend for Panel 1
    legend_elements = [
        mpatches.Patch(color='#64B5F6', label='Active Nodes'),
        plt.Line2D([0], [0], color='#90A4AE', linewidth=1, label='Active Edges'),
        plt.Line2D([0], [0], color='#B0BEC5', linewidth=1, linestyle='--', label='Dormant Edges'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=8, framealpha=0.9)

    # ── Panel 2: After Failure ──
    ax = axes[1]
    # Color-code components
    components = list(nx.connected_components(G_failed))
    cmap = plt.cm.Set2
    node_colors = {}
    for idx, comp in enumerate(components):
        color = cmap(idx % 8)
        for node in comp:
            node_colors[node] = color

    surviving_nodes = list(G_failed.nodes())
    colors_list = [node_colors[n] for n in surviving_nodes]

    nx.draw_networkx_nodes(G_failed, pos, nodelist=surviving_nodes, ax=ax,
                           node_color=colors_list, node_size=120,
                           edgecolors='#424242', linewidths=0.8)
    nx.draw_networkx_edges(G_failed, pos, ax=ax,
                           edge_color='#90A4AE', width=1.0, alpha=0.7)

    # Overlay failed nodes as red X markers
    if failed_nodes:
        failed_x = [pos[n][0] for n in failed_nodes if n in pos]
        failed_y = [pos[n][1] for n in failed_nodes if n in pos]
        ax.scatter(failed_x, failed_y, c='red', marker='x', s=100,
                   linewidths=2, zorder=5, alpha=0.7)

    ax.set_title(f"2. After Failure\n({len(components)} components, "
                 f"{len(failed_nodes)} nodes removed)", fontsize=12)
    ax.axis('off')

    legend_elements = [
        plt.Line2D([0], [0], marker='x', color='red', linestyle='None',
                    markersize=10, label=f'Failed Nodes ({len(failed_nodes)})'),
        mpatches.Patch(color=cmap(0), label=f'Component 1'),
        mpatches.Patch(color=cmap(1), label=f'Component 2'),
    ]
    if len(components) > 2:
        legend_elements.append(mpatches.Patch(color=cmap(2), label=f'Component 3+'))
    ax.legend(handles=legend_elements, loc='lower left', fontsize=8, framealpha=0.9)

    # ── Panel 3: After Healing ──
    ax = axes[2]
    nx.draw_networkx_nodes(G_healed, pos, ax=ax,
                           node_color='#81C784', node_size=120,
                           edgecolors='#2E7D32', linewidths=0.8)
    # Draw original surviving edges
    original_edges = list(G_failed.edges())
    nx.draw_networkx_edges(G_healed, pos, edgelist=original_edges, ax=ax,
                           edge_color='#90A4AE', width=1.0, alpha=0.7)
    # Highlight healed edges
    if edges_added:
        nx.draw_networkx_edges(G_healed, pos, edgelist=edges_added, ax=ax,
                               edge_color='#F44336', width=2.5, alpha=0.9,
                               style='solid')

    healed_status = '✓ Connected' if metrics['is_fully_healed'] else '✗ Fragmented'
    ax.set_title(f"3. After Healing ({healed_status})\n"
                 f"({len(edges_added)} edges activated, "
                 f"cost={metrics['total_healing_cost']:.1f})", fontsize=12)
    ax.axis('off')

    legend_elements = [
        mpatches.Patch(color='#81C784', label='Surviving Nodes'),
        plt.Line2D([0], [0], color='#90A4AE', linewidth=1, label='Original Edges'),
        plt.Line2D([0], [0], color='#F44336', linewidth=2.5, label='Healed Edges'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=8, framealpha=0.9)

    plt.tight_layout()
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================================
# 2. HEALING ANIMATION GIF
# ============================================================================

def create_healing_animation(result, filename='healing_animation.gif', fps=1):
    """
    Generate step-by-step healing animation GIF.
    
    Each frame shows the network with one additional healed edge.
    """
    healing_steps = result['healing_steps']
    pos = result['pos']
    edges_added = result['edges_added']
    G_initial = result['G_initial']
    failed_nodes = result['failed_nodes']

    if len(healing_steps) < 2:
        print("  Warning: Not enough healing steps for animation")
        return None

    fig, ax = plt.subplots(figsize=(10, 8))

    def update(frame):
        ax.clear()
        curr = healing_steps[frame]
        n_comps = nx.number_connected_components(curr)

        # Color-code components
        components = list(nx.connected_components(curr))
        cmap = plt.cm.Set2
        node_colors = {}
        for idx, comp in enumerate(components):
            color = cmap(idx % 8)
            for node in comp:
                node_colors[node] = color

        nodes_list = list(curr.nodes())
        colors_list = [node_colors.get(n, '#64B5F6') for n in nodes_list]

        nx.draw_networkx_nodes(curr, pos, nodelist=nodes_list, ax=ax,
                               node_color=colors_list, node_size=150,
                               edgecolors='#424242', linewidths=0.8)
        nx.draw_networkx_edges(curr, pos, ax=ax,
                               edge_color='#90A4AE', width=1.0, alpha=0.7)

        # Show failed nodes as faded X
        if failed_nodes:
            fx = [pos[n][0] for n in failed_nodes if n in pos]
            fy = [pos[n][1] for n in failed_nodes if n in pos]
            ax.scatter(fx, fy, c='red', marker='x', s=80, linewidths=1.5,
                       alpha=0.3, zorder=5)

        # Highlight newly added edge for this frame
        if frame > 0 and frame - 1 < len(edges_added):
            new_edge = [edges_added[frame - 1]]
            nx.draw_networkx_edges(curr, pos, edgelist=new_edge, ax=ax,
                                   edge_color='#F44336', width=3.5,
                                   style='solid', alpha=0.9)

        # All previously added edges in orange
        if frame > 1:
            prev_edges = edges_added[:frame - 1]
            if prev_edges:
                nx.draw_networkx_edges(curr, pos, edgelist=prev_edges, ax=ax,
                                       edge_color='#FF9800', width=2.0,
                                       style='solid', alpha=0.7)

        status = "✓ CONNECTED" if n_comps == 1 else f"{n_comps} Components"
        title = (f"Healing Step {frame}/{len(healing_steps)-1}  —  {status}")
        if frame == 0:
            title = f"After Failure  —  {n_comps} Disconnected Components"
        ax.set_title(title, fontsize=14, fontweight='bold',
                     color='#2E7D32' if n_comps == 1 else '#D32F2F')
        ax.axis('off')

    ani = FuncAnimation(fig, update, frames=range(len(healing_steps)),
                        interval=1500, repeat=True, repeat_delay=3000)

    filepath = os.path.join(OUTPUT_DIR, filename)
    ani.save(filepath, writer='pillow', dpi=120)
    plt.close(fig)
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================================
# 3. METRICS COMPARISON HEATMAP
# ============================================================================

def plot_metrics_heatmap(filename='metrics_heatmap.png'):
    """
    Generate heatmap comparing topologies × failure modes across metrics.
    """
    topologies = ['watts_strogatz', 'barabasi_albert', 'erdos_renyi', 'grid']
    failure_modes = ['random', 'targeted']
    metric_names = ['healing_ratio', 'edges_activated', 'total_healing_cost']

    data = {}
    for topo in topologies:
        for fm in failure_modes:
            res = run_simulation(
                topology=topo, n=100, failure_rate=0.15,
                failure_mode=fm, healer='kruskal_dsu',
                dormant_budget=0.30, seed=42, verbose=False
            )
            key = f"{topo}\n({fm})"
            data[key] = {
                'healing_ratio': res['metrics']['healing_ratio'],
                'edges_activated': res['metrics']['edges_activated'],
                'total_healing_cost': res['metrics']['total_healing_cost'],
            }

    # Build matrix
    labels = list(data.keys())
    matrix = np.array([[data[k]['healing_ratio'] * 100,
                         data[k]['edges_activated'],
                         data[k]['total_healing_cost']] for k in labels])

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(matrix, cmap='YlGnBu', aspect='auto')

    ax.set_xticks(range(3))
    ax.set_xticklabels(['Healing Ratio (%)', 'Edges Activated', 'Total Cost'], fontsize=10)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)

    # Annotate cells
    for i in range(len(labels)):
        for j in range(3):
            val = matrix[i, j]
            fmt = f"{val:.0f}" if j > 0 else f"{val:.1f}%"
            ax.text(j, i, fmt, ha='center', va='center', fontsize=10,
                    color='white' if val > np.median(matrix[:, j]) else 'black')

    ax.set_title('Healing Metrics: Topology × Failure Mode',
                 fontsize=14, fontweight='bold')
    fig.colorbar(im, ax=ax, shrink=0.8)

    plt.tight_layout()
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================================
# 4. ADAPTIVE DORMANT POOL VISUALIZATION
# ============================================================================

def plot_adaptive_comparison(filename='adaptive_comparison.png'):
    """
    Innovation: Compare static dormant pool vs adaptive dormant pool healing.
    """
    from self_healing_network import (
        generate_graph, generate_dormant_edges, simulate_failure,
        heal_kruskal_dsu, generate_adaptive_dormant, compute_metrics
    )

    n = 100
    G, pos = generate_graph('watts_strogatz', n, seed=42)
    static_dormant = generate_dormant_edges(G, pos, budget_ratio=0.20, seed=42)
    G_failed, failed_nodes = simulate_failure(G, mode='random', failure_rate=0.20, seed=42)

    # Static healing
    G_healed_static, edges_static, _ = heal_kruskal_dsu(G_failed, static_dormant)
    m_static = compute_metrics(G, G_failed, G_healed_static, failed_nodes, edges_static)

    # Adaptive healing: combine static + adaptive
    adaptive_dormant = generate_adaptive_dormant(G_failed, pos, budget=15, seed=42)
    combined_dormant = sorted(static_dormant + adaptive_dormant,
                               key=lambda x: x[2]['weight'])
    G_healed_adaptive, edges_adaptive, _ = heal_kruskal_dsu(G_failed, combined_dormant)
    m_adaptive = compute_metrics(G, G_failed, G_healed_adaptive, failed_nodes, edges_adaptive)

    # Plot comparison
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle('Innovation: Static vs Adaptive Dormant Pool',
                 fontsize=15, fontweight='bold')

    for idx, (G_h, edges, m, label) in enumerate([
        (G_healed_static, edges_static, m_static, 'Static Dormant Pool'),
        (G_healed_adaptive, edges_adaptive, m_adaptive, 'Static + Adaptive Pool'),
    ]):
        ax = axes[idx]
        color = '#81C784' if m['is_fully_healed'] else '#FFCC80'
        nx.draw_networkx_nodes(G_h, pos, ax=ax, node_color=color,
                               node_size=100, edgecolors='#424242', linewidths=0.5)
        nx.draw_networkx_edges(G_h, pos, ax=ax, edge_color='#BDBDBD',
                               width=0.8, alpha=0.5)
        if edges:
            nx.draw_networkx_edges(G_h, pos, edgelist=edges, ax=ax,
                                   edge_color='#F44336', width=2.5)
        # Failed nodes
        fx = [pos[n][0] for n in failed_nodes if n in pos]
        fy = [pos[n][1] for n in failed_nodes if n in pos]
        ax.scatter(fx, fy, c='red', marker='x', s=60, linewidths=1.5, alpha=0.3)

        status = '✓ Connected' if m['is_fully_healed'] else '✗ Fragmented'
        ax.set_title(f"{label}\n{status} | Edges: {m['edges_activated']} | "
                     f"Cost: {m['total_healing_cost']:.1f}", fontsize=11)
        ax.axis('off')

    plt.tight_layout()
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Saved: {filepath}")
    return filepath


# ============================================================================
# MAIN — GENERATE ALL VISUALIZATIONS
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  GENERATING VISUALIZATIONS")
    print("=" * 60)

    from self_healing_network import generate_graph, generate_dormant_edges, simulate_failure, heal_kruskal_dsu, compute_metrics

    # 1. Main 3-panel for Watts-Strogatz with enough failures to cause fragmentation
    print("\n[1/6] Three-panel visualization (Watts-Strogatz, k=2, 30% failure)...")
    result_ws = run_simulation(topology='watts_strogatz', n=60, failure_rate=0.30,
                                healer='kruskal_dsu', seed=42, verbose=True,
                                dormant_budget=0.40)
    plot_three_panel(result_ws, 'three_panel_ws.png')

    # 2. Three-panel for Barabási-Albert with targeted attack (dramatic)
    print("\n[2/6] Three-panel visualization (Barabási-Albert, targeted)...")
    result_ba = run_simulation(topology='barabasi_albert', n=60, failure_rate=0.15,
                                failure_mode='targeted', healer='kruskal_dsu',
                                seed=42, verbose=True, dormant_budget=0.50)
    plot_three_panel(result_ba, 'three_panel_ba.png', ' — Barabási-Albert (Targeted Attack)')

    # 3. Healing animation — use a scenario that actually fragments
    print("\n[3/6] Healing animation GIF...")
    # Use BA targeted since it creates many components
    if len(result_ba['healing_steps']) >= 2:
        create_healing_animation(result_ba, 'healing_animation.gif')
    else:
        # Fallback: use WS with higher failure
        result_anim = run_simulation(topology='watts_strogatz', n=50, failure_rate=0.35,
                                      healer='kruskal_dsu', seed=42, verbose=False,
                                      dormant_budget=0.50)
        if len(result_anim['healing_steps']) >= 2:
            create_healing_animation(result_anim, 'healing_animation.gif')
        else:
            print("  Warning: Could not produce animation with enough steps")

    # 4. Metrics heatmap
    print("\n[4/6] Metrics heatmap...")
    plot_metrics_heatmap()

    # 5. Adaptive dormant comparison — use params that show the difference
    print("\n[5/6] Adaptive dormant pool comparison...")
    plot_adaptive_comparison()

    # 6. Three-panel for Cascading failure (innovation)
    print("\n[6/6] Three-panel for cascading failure...")
    result_casc = run_simulation(topology='watts_strogatz', n=60, failure_rate=0.25,
                                  failure_mode='cascading', healer='kruskal_dsu',
                                  seed=42, verbose=True, dormant_budget=0.40)
    plot_three_panel(result_casc, 'three_panel_cascading.png', ' — Cascading Failure')

    print("\n" + "=" * 60)
    print("  ALL VISUALIZATIONS COMPLETE")
    print(f"  Output directory: {os.path.abspath(OUTPUT_DIR)}/")
    print("=" * 60)

