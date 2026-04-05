"""
Experimental Suite for Self-Healing Network Connectivity
=========================================================
Advanced Graph Theory — Digital Assignment II

Runs 6 comprehensive experiments and saves results as CSV + plots.

Experiments:
  1. Failure Rate Sweep (5%–50%)
  2. Topology Comparison (WS vs BA vs ER vs Grid)
  3. Scalability Analysis (50–500 nodes)
  4. Algorithm Comparison (Kruskal-DSU vs Random vs Degree-Based)
  5. Dormant Edge Budget Sweep (10%–60%)
  6. Cascading Failure Simulation (multi-round)

Author : Fang
Date   : April 2026
"""

import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving plots
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import time

from self_healing_network import (
    generate_graph, generate_dormant_edges, simulate_failure,
    detect_partitions_bfs, heal_kruskal_dsu, heal_random,
    heal_degree_based, generate_adaptive_dormant,
    compute_metrics, compute_metrics_quick, run_simulation, DSU
)

# ── Global plot style ──────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': '#fafafa',
    'axes.facecolor': '#fafafa',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'legend.fontsize': 10,
    'figure.dpi': 150,
})

COLORS = {
    'kruskal_dsu': '#2196F3',
    'random': '#FF5722',
    'degree_based': '#4CAF50',
    'watts_strogatz': '#2196F3',
    'barabasi_albert': '#FF9800',
    'erdos_renyi': '#9C27B0',
    'grid': '#4CAF50',
}

OUTPUT_DIR = 'results'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_csv(filename, headers, rows):
    """Save experiment data to CSV."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  Saved: {filepath}")


# ============================================================================
# EXPERIMENT 1: Failure Rate Sweep
# ============================================================================

def experiment_1_failure_sweep():
    """
    Test healing effectiveness across increasing failure rates (5%–50%).
    
    Hypothesis: Healing ratio degrades as failure rate increases because
    more dormant edges get invalidated (endpoints removed).
    """
    print("\n" + "=" * 60)
    print("  EXPERIMENT 1: Failure Rate Sweep")
    print("=" * 60)

    failure_rates = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    results = []

    for fr in failure_rates:
        res = run_simulation(
            topology='watts_strogatz', n=100, failure_rate=fr,
            failure_mode='random', healer='kruskal_dsu',
            dormant_budget=0.30, seed=42, verbose=False
        )
        m = res['metrics']
        results.append({
            'failure_rate': fr,
            'components_failed': m['components_after_failure'],
            'components_healed': m['components_after_healing'],
            'healing_ratio': m['healing_ratio'],
            'edges_activated': m['edges_activated'],
            'total_cost': m['total_healing_cost'],
            'is_healed': m['is_fully_healed'],
        })
        print(f"  FR={fr*100:4.0f}% → Comps: {m['components_after_failure']:2d}→"
              f"{m['components_after_healing']:2d} | "
              f"Healed: {m['healing_ratio']:.1%} | Edges: {m['edges_activated']}")

    # Save CSV
    save_csv('exp1_failure_sweep.csv',
             ['failure_rate', 'components_failed', 'components_healed',
              'healing_ratio', 'edges_activated', 'total_cost', 'is_healed'],
             [[r[k] for k in ['failure_rate', 'components_failed', 'components_healed',
                               'healing_ratio', 'edges_activated', 'total_cost', 'is_healed']]
              for r in results])

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Experiment 1: Effect of Failure Rate on Healing', fontsize=15, fontweight='bold')

    frs = [r['failure_rate'] * 100 for r in results]
    ax1.plot(frs, [r['healing_ratio'] * 100 for r in results],
             'o-', color='#2196F3', linewidth=2, markersize=8, label='Healing Ratio')
    ax1.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='Full Recovery')
    ax1.set_xlabel('Failure Rate (%)')
    ax1.set_ylabel('Healing Ratio (%)')
    ax1.set_title('Healing Effectiveness vs Failure Rate')
    ax1.legend()
    ax1.set_ylim(-5, 110)

    ax2.bar(frs, [r['components_failed'] for r in results],
            width=3.5, alpha=0.7, color='#FF5722', label='After Failure')
    ax2.bar(frs, [r['components_healed'] for r in results],
            width=3.5, alpha=0.7, color='#4CAF50', label='After Healing')
    ax2.set_xlabel('Failure Rate (%)')
    ax2.set_ylabel('Connected Components')
    ax2.set_title('Component Count Before & After Healing')
    ax2.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'exp1_failure_sweep.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  Plot saved: exp1_failure_sweep.png")
    return results


# ============================================================================
# EXPERIMENT 2: Topology Comparison
# ============================================================================

def experiment_2_topology_comparison():
    """
    Compare healing effectiveness across 4 graph topologies.
    
    Hypothesis: Scale-free (BA) graphs are more vulnerable to targeted attacks
    but have more dormant edge options. Grid graphs have poor healing due to
    low local redundancy.
    """
    print("\n" + "=" * 60)
    print("  EXPERIMENT 2: Topology Comparison")
    print("=" * 60)

    topologies = ['watts_strogatz', 'barabasi_albert', 'erdos_renyi', 'grid']
    failure_modes = ['random', 'targeted']
    results = []

    for topo in topologies:
        for fm in failure_modes:
            res = run_simulation(
                topology=topo, n=100, failure_rate=0.15,
                failure_mode=fm, healer='kruskal_dsu',
                dormant_budget=0.30, seed=42, verbose=False
            )
            m = res['metrics']
            results.append({
                'topology': topo,
                'failure_mode': fm,
                'components_failed': m['components_after_failure'],
                'healing_ratio': m['healing_ratio'],
                'edges_activated': m['edges_activated'],
                'total_cost': m['total_healing_cost'],
                'diameter_healed': m.get('diameter_healed', -1),
                'avg_path_healed': m.get('avg_path_length_healed', -1),
                'is_healed': m['is_fully_healed'],
            })
            print(f"  {topo:20s} | {fm:10s} → Comps: {m['components_after_failure']:2d} | "
                  f"Heal: {m['healing_ratio']:.1%} | Cost: {m['total_healing_cost']:.1f}")

    # Save CSV
    save_csv('exp2_topology_comparison.csv',
             ['topology', 'failure_mode', 'components_failed', 'healing_ratio',
              'edges_activated', 'total_cost', 'diameter_healed', 'avg_path_healed', 'is_healed'],
             [[r[k] for k in ['topology', 'failure_mode', 'components_failed', 'healing_ratio',
                               'edges_activated', 'total_cost', 'diameter_healed',
                               'avg_path_healed', 'is_healed']]
              for r in results])

    # Plot — grouped bar chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Experiment 2: Topology Comparison', fontsize=15, fontweight='bold')

    x = np.arange(len(topologies))
    width = 0.35

    random_hr = [r['healing_ratio'] * 100 for r in results if r['failure_mode'] == 'random']
    targeted_hr = [r['healing_ratio'] * 100 for r in results if r['failure_mode'] == 'targeted']

    bars1 = ax1.bar(x - width / 2, random_hr, width, label='Random Failure',
                    color='#2196F3', alpha=0.8)
    bars2 = ax1.bar(x + width / 2, targeted_hr, width, label='Targeted Attack',
                    color='#FF5722', alpha=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([t.replace('_', '\n') for t in topologies], fontsize=9)
    ax1.set_ylabel('Healing Ratio (%)')
    ax1.set_title('Healing Ratio by Topology & Failure Mode')
    ax1.legend()
    ax1.set_ylim(0, 115)
    ax1.axhline(y=100, color='green', linestyle='--', alpha=0.3)

    random_cost = [r['total_cost'] for r in results if r['failure_mode'] == 'random']
    targeted_cost = [r['total_cost'] for r in results if r['failure_mode'] == 'targeted']

    ax2.bar(x - width / 2, random_cost, width, label='Random Failure',
            color='#2196F3', alpha=0.8)
    ax2.bar(x + width / 2, targeted_cost, width, label='Targeted Attack',
            color='#FF5722', alpha=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels([t.replace('_', '\n') for t in topologies], fontsize=9)
    ax2.set_ylabel('Total Healing Cost')
    ax2.set_title('Healing Cost by Topology & Failure Mode')
    ax2.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'exp2_topology_comparison.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  Plot saved: exp2_topology_comparison.png")
    return results


# ============================================================================
# EXPERIMENT 3: Scalability Analysis
# ============================================================================

def experiment_3_scalability():
    """
    Measure how healing performance scales with graph size (50–500 nodes).
    
    Tracks runtime, healing ratio, and edge count.
    """
    print("\n" + "=" * 60)
    print("  EXPERIMENT 3: Scalability Analysis")
    print("=" * 60)

    sizes = [50, 75, 100, 150, 200, 300, 400, 500]
    results = []

    for n in sizes:
        start = time.time()
        res = run_simulation(
            topology='watts_strogatz', n=n, failure_rate=0.15,
            failure_mode='random', healer='kruskal_dsu',
            dormant_budget=0.30, seed=42, verbose=False
        )
        total_time = (time.time() - start) * 1000
        m = res['metrics']
        results.append({
            'n': n,
            'total_time_ms': round(total_time, 2),
            'heal_time_ms': m['heal_time_ms'],
            'healing_ratio': m['healing_ratio'],
            'edges_activated': m['edges_activated'],
            'components_failed': m['components_after_failure'],
            'is_healed': m['is_fully_healed'],
        })
        print(f"  n={n:4d} → Time: {total_time:7.1f}ms | "
              f"Heal: {m['healing_ratio']:.1%} | Edges: {m['edges_activated']}")

    # Save CSV
    save_csv('exp3_scalability.csv',
             ['n', 'total_time_ms', 'heal_time_ms', 'healing_ratio',
              'edges_activated', 'components_failed', 'is_healed'],
             [[r[k] for k in ['n', 'total_time_ms', 'heal_time_ms', 'healing_ratio',
                               'edges_activated', 'components_failed', 'is_healed']]
              for r in results])

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Experiment 3: Scalability Analysis', fontsize=15, fontweight='bold')

    ns = [r['n'] for r in results]
    ax1.plot(ns, [r['total_time_ms'] for r in results],
             'o-', color='#FF5722', linewidth=2, markersize=8, label='Total Time')
    ax1.plot(ns, [r['heal_time_ms'] for r in results],
             's--', color='#2196F3', linewidth=2, markersize=7, label='Heal Phase Only')
    ax1.set_xlabel('Number of Nodes')
    ax1.set_ylabel('Time (ms)')
    ax1.set_title('Runtime vs Graph Size')
    ax1.legend()

    ax2.plot(ns, [r['healing_ratio'] * 100 for r in results],
             'o-', color='#4CAF50', linewidth=2, markersize=8)
    ax2.set_xlabel('Number of Nodes')
    ax2.set_ylabel('Healing Ratio (%)')
    ax2.set_title('Healing Effectiveness vs Graph Size')
    ax2.set_ylim(-5, 110)
    ax2.axhline(y=100, color='green', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'exp3_scalability.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  Plot saved: exp3_scalability.png")
    return results


# ============================================================================
# EXPERIMENT 4: Algorithm Comparison
# ============================================================================

def experiment_4_algorithm_comparison():
    """
    Compare Kruskal-DSU (proposed) vs Random vs Degree-Based healing.
    
    Hypothesis: Kruskal-DSU achieves the best cost-effectiveness by minimizing
    total healing cost while maintaining restoration capability.
    """
    print("\n" + "=" * 60)
    print("  EXPERIMENT 4: Algorithm Comparison")
    print("=" * 60)

    healers = ['kruskal_dsu', 'random', 'degree_based']
    failure_rates = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    results = []

    for healer in healers:
        for fr in failure_rates:
            res = run_simulation(
                topology='watts_strogatz', n=100, failure_rate=fr,
                failure_mode='random', healer=healer,
                dormant_budget=0.30, seed=42, verbose=False
            )
            m = res['metrics']
            results.append({
                'healer': healer,
                'failure_rate': fr,
                'healing_ratio': m['healing_ratio'],
                'edges_activated': m['edges_activated'],
                'total_cost': m['total_healing_cost'],
                'avg_cost': m['avg_edge_cost'],
                'is_healed': m['is_fully_healed'],
                'heal_time_ms': m['heal_time_ms'],
            })

    # Print summary
    for healer in healers:
        hrs = [r for r in results if r['healer'] == healer]
        avg_hr = np.mean([r['healing_ratio'] for r in hrs])
        avg_cost = np.mean([r['total_cost'] for r in hrs])
        print(f"  {healer:15s} → Avg Heal Ratio: {avg_hr:.1%} | Avg Cost: {avg_cost:.1f}")

    # Save CSV
    save_csv('exp4_algorithm_comparison.csv',
             ['healer', 'failure_rate', 'healing_ratio', 'edges_activated',
              'total_cost', 'avg_cost', 'is_healed', 'heal_time_ms'],
             [[r[k] for k in ['healer', 'failure_rate', 'healing_ratio', 'edges_activated',
                               'total_cost', 'avg_cost', 'is_healed', 'heal_time_ms']]
              for r in results])

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Experiment 4: Algorithm Comparison', fontsize=15, fontweight='bold')

    for healer in healers:
        hrs = [r for r in results if r['healer'] == healer]
        frs = [r['failure_rate'] * 100 for r in hrs]
        label = healer.replace('_', ' ').title()
        ax1.plot(frs, [r['healing_ratio'] * 100 for r in hrs],
                 'o-', color=COLORS[healer], linewidth=2, markersize=7, label=label)
        ax2.plot(frs, [r['total_cost'] for r in hrs],
                 's-', color=COLORS[healer], linewidth=2, markersize=7, label=label)

    ax1.set_xlabel('Failure Rate (%)')
    ax1.set_ylabel('Healing Ratio (%)')
    ax1.set_title('Healing Ratio Comparison')
    ax1.legend()
    ax1.set_ylim(-5, 115)
    ax1.axhline(y=100, color='green', linestyle='--', alpha=0.3)

    ax2.set_xlabel('Failure Rate (%)')
    ax2.set_ylabel('Total Healing Cost')
    ax2.set_title('Cost Comparison')
    ax2.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'exp4_algorithm_comparison.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  Plot saved: exp4_algorithm_comparison.png")
    return results


# ============================================================================
# EXPERIMENT 5: Dormant Edge Budget Sweep
# ============================================================================

def experiment_5_dormant_budget():
    """
    Evaluate effect of dormant edge pool size on healing capability.
    
    Hypothesis: Larger dormant pools improve healing but with diminishing
    returns beyond a certain threshold.
    """
    print("\n" + "=" * 60)
    print("  EXPERIMENT 5: Dormant Edge Budget Sweep")
    print("=" * 60)

    budgets = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]
    results = []

    for budget in budgets:
        res = run_simulation(
            topology='watts_strogatz', n=100, failure_rate=0.20,
            failure_mode='random', healer='kruskal_dsu',
            dormant_budget=budget, seed=42, verbose=False
        )
        m = res['metrics']
        results.append({
            'budget': budget,
            'dormant_count': len(res['dormant_edges']),
            'healing_ratio': m['healing_ratio'],
            'edges_activated': m['edges_activated'],
            'total_cost': m['total_healing_cost'],
            'is_healed': m['is_fully_healed'],
        })
        print(f"  Budget={budget*100:4.0f}% → Dormant: {len(res['dormant_edges']):3d} | "
              f"Heal: {m['healing_ratio']:.1%} | Activated: {m['edges_activated']}")

    # Save CSV
    save_csv('exp5_dormant_budget.csv',
             ['budget', 'dormant_count', 'healing_ratio', 'edges_activated',
              'total_cost', 'is_healed'],
             [[r[k] for k in ['budget', 'dormant_count', 'healing_ratio',
                               'edges_activated', 'total_cost', 'is_healed']]
              for r in results])

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Experiment 5: Dormant Edge Budget Analysis', fontsize=15, fontweight='bold')

    bs = [r['budget'] * 100 for r in results]
    ax1.plot(bs, [r['healing_ratio'] * 100 for r in results],
             'o-', color='#2196F3', linewidth=2, markersize=8)
    ax1.axhline(y=100, color='green', linestyle='--', alpha=0.3, label='Full Recovery')
    ax1.set_xlabel('Dormant Budget (% of active edges)')
    ax1.set_ylabel('Healing Ratio (%)')
    ax1.set_title('Healing Ratio vs Dormant Budget')
    ax1.set_ylim(-5, 115)
    ax1.legend()

    ax2.bar(bs, [r['dormant_count'] for r in results],
            width=4, alpha=0.6, color='#FF9800', label='Total Dormant')
    ax2.bar(bs, [r['edges_activated'] for r in results],
            width=4, alpha=0.8, color='#4CAF50', label='Activated')
    ax2.set_xlabel('Dormant Budget (% of active edges)')
    ax2.set_ylabel('Edge Count')
    ax2.set_title('Dormant Pool vs Edges Used')
    ax2.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'exp5_dormant_budget.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  Plot saved: exp5_dormant_budget.png")
    return results


# ============================================================================
# EXPERIMENT 6: Cascading Failure Simulation
# ============================================================================

def experiment_6_cascading():
    """
    Innovation Extension: Test resilience under multi-round cascading failures.
    
    Simulates 5 rounds of:
      1. Random failure (10% of surviving nodes per round)
      2. Immediate DSU healing attempt
    
    Measures cumulative damage and recovery capability.
    """
    print("\n" + "=" * 60)
    print("  EXPERIMENT 6: Cascading Failure Simulation")
    print("=" * 60)

    from self_healing_network import generate_graph, generate_dormant_edges, DSU
    import networkx as nx
    import random as rng_module

    n = 150
    G_orig, pos = generate_graph('watts_strogatz', n, seed=42, k=4, p=0.1)
    full_dormant = generate_dormant_edges(G_orig, pos, budget_ratio=0.50, seed=42)

    G_current = G_orig.copy()
    all_failed = []
    rounds = 5
    results = []

    for round_num in range(1, rounds + 1):
        # Fail 10% of surviving nodes
        surviving = list(G_current.nodes())
        num_fail = max(int(len(surviving) * 0.10), 1)
        rng = rng_module.Random(42 + round_num)
        failures = rng.sample(surviving, min(num_fail, len(surviving)))
        all_failed.extend(failures)
        G_current.remove_nodes_from(failures)

        comps_before = nx.number_connected_components(G_current)

        # Heal using remaining dormant edges
        surviving_set = set(G_current.nodes())
        valid_dormant = [
            (u, v, d) for u, v, d in full_dormant
            if u in surviving_set and v in surviving_set
            and not G_current.has_edge(u, v)
        ]

        dsu = DSU(surviving_set)
        for u, v in G_current.edges():
            dsu.union(u, v)

        edges_this_round = []
        for u, v, data in valid_dormant:
            if dsu.component_count <= 1:
                break
            if dsu.union(u, v):
                G_current.add_edge(u, v, **data)
                edges_this_round.append((u, v))

        comps_after = nx.number_connected_components(G_current)

        result = {
            'round': round_num,
            'nodes_remaining': len(surviving_set) - len(failures),
            'nodes_failed_this_round': len(failures),
            'total_failed': len(all_failed),
            'components_before_heal': comps_before,
            'components_after_heal': comps_after,
            'edges_activated': len(edges_this_round),
            'is_connected': comps_after == 1,
        }
        results.append(result)
        print(f"  Round {round_num}: Failed {len(failures)} nodes | "
              f"Comps: {comps_before}→{comps_after} | "
              f"Edges: {len(edges_this_round)} | "
              f"{'✓ Connected' if comps_after == 1 else '✗ Fragmented'}")

    # Save CSV
    save_csv('exp6_cascading.csv',
             ['round', 'nodes_remaining', 'nodes_failed_this_round', 'total_failed',
              'components_before_heal', 'components_after_heal', 'edges_activated', 'is_connected'],
             [[r[k] for k in ['round', 'nodes_remaining', 'nodes_failed_this_round', 'total_failed',
                               'components_before_heal', 'components_after_heal',
                               'edges_activated', 'is_connected']]
              for r in results])

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Experiment 6: Cascading Failure Resilience', fontsize=15, fontweight='bold')

    rounds_x = [r['round'] for r in results]

    ax1.plot(rounds_x, [r['components_before_heal'] for r in results],
             'o--', color='#FF5722', linewidth=2, markersize=8, label='Before Healing')
    ax1.plot(rounds_x, [r['components_after_heal'] for r in results],
             's-', color='#4CAF50', linewidth=2, markersize=8, label='After Healing')
    ax1.axhline(y=1, color='green', linestyle='--', alpha=0.3)
    ax1.set_xlabel('Failure Round')
    ax1.set_ylabel('Connected Components')
    ax1.set_title('Components per Round')
    ax1.legend()
    ax1.set_xticks(rounds_x)

    ax2.bar(rounds_x, [r['nodes_failed_this_round'] for r in results],
            alpha=0.7, color='#FF5722', label='Nodes Failed')
    ax2_twin = ax2.twinx()
    ax2_twin.plot(rounds_x, [r['edges_activated'] for r in results],
                  'o-', color='#2196F3', linewidth=2, markersize=8, label='Edges Activated')
    ax2.set_xlabel('Failure Round')
    ax2.set_ylabel('Nodes Failed', color='#FF5722')
    ax2_twin.set_ylabel('Edges Activated', color='#2196F3')
    ax2.set_title('Failures vs Healing Effort per Round')
    ax2.set_xticks(rounds_x)

    # Combined legend
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'exp6_cascading.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("  Plot saved: exp6_cascading.png")
    return results


# ============================================================================
# SUMMARY TABLE
# ============================================================================

def generate_summary_table(all_results):
    """Generate a summary comparison table across all experiments."""
    print("\n" + "=" * 60)
    print("  SUMMARY TABLE")
    print("=" * 60)

    # Create a text-based summary
    summary = []
    summary.append(f"{'Experiment':<35} {'Key Finding':<50}")
    summary.append("-" * 85)

    # Exp 1 summary
    exp1 = all_results.get('exp1', [])
    if exp1:
        max_fully_healed = max([r['failure_rate'] for r in exp1 if r['is_healed']], default=0)
        finding = f"Full heal up to {int(max_fully_healed*100)}% failure"
        summary.append(f"{'1. Failure Rate Sweep':<35} {finding:<50}")

    # Exp 2 summary
    exp2 = all_results.get('exp2', [])
    if exp2:
        best_topo = max([r for r in exp2 if r['failure_mode'] == 'random'],
                        key=lambda x: x['healing_ratio'])
        hr_pct = f"{best_topo['healing_ratio']:.0%}"
        finding = f"Best: {best_topo['topology']} ({hr_pct})"
        summary.append(f"{'2. Topology Comparison':<35} {finding:<50}")

    # Exp 3 summary
    exp3 = all_results.get('exp3', [])
    if exp3:
        max_time = max(r['total_time_ms'] for r in exp3)
        finding = f"Max time: {max_time:.0f}ms at n=500"
        summary.append(f"{'3. Scalability (50-500)':<35} {finding:<50}")

    # Exp 4 summary
    exp4 = all_results.get('exp4', [])
    if exp4:
        for healer in ['kruskal_dsu', 'random', 'degree_based']:
            hrs = [r for r in exp4 if r['healer'] == healer]
            avg_cost = np.mean([r['total_cost'] for r in hrs])
            label = f"4. {healer}"
            finding = f"Avg cost: {avg_cost:.1f}"
            summary.append(f"{label:<35} {finding:<50}")

    # Exp 5 summary
    exp5 = all_results.get('exp5', [])
    if exp5:
        min_budget = min([r['budget'] for r in exp5 if r['is_healed']], default=0)
        finding = f"Min budget for full heal: {min_budget*100:.0f}%"
        summary.append(f"{'5. Dormant Budget':<35} {finding:<50}")

    # Exp 6 summary
    exp6 = all_results.get('exp6', [])
    if exp6:
        rounds_connected = sum(1 for r in exp6 if r['is_connected'])
        finding = f"Connected after {rounds_connected}/5 rounds"
        summary.append(f"{'6. Cascading Failures':<35} {finding:<50}")

    for line in summary:
        print(f"  {line}")

    # Save
    with open(os.path.join(OUTPUT_DIR, 'summary.txt'), 'w') as f:
        f.write('\n'.join(summary))
    print(f"\n  Saved: {OUTPUT_DIR}/summary.txt")


# ============================================================================
# MAIN — RUN ALL EXPERIMENTS
# ============================================================================

if __name__ == '__main__':
    print("\n" + "█" * 60)
    print("  RUNNING ALL EXPERIMENTS")
    print("  Self-Healing Network Connectivity — DA-II")
    print("█" * 60)

    all_results = {}

    all_results['exp1'] = experiment_1_failure_sweep()
    all_results['exp2'] = experiment_2_topology_comparison()
    all_results['exp3'] = experiment_3_scalability()
    all_results['exp4'] = experiment_4_algorithm_comparison()
    all_results['exp5'] = experiment_5_dormant_budget()
    all_results['exp6'] = experiment_6_cascading()

    generate_summary_table(all_results)

    print("\n" + "█" * 60)
    print("  ALL EXPERIMENTS COMPLETE")
    print(f"  Results saved to: {os.path.abspath(OUTPUT_DIR)}/")
    print("█" * 60)
