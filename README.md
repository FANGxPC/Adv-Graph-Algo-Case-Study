# 🔧 Self-Healing Network Connectivity Using BFS-DSU Hybrid Recovery

**Advanced Graph Theory — Digital Assignment II (Case Study)**

> Automatic detection and repair of network fragmentation after node failures using a BFS-DSU Hybrid Recovery Algorithm with locality-aware Kruskal's edge activation.

---

## 📌 Quick Overview

| Item | Details |
|---|---|
| **Topic** | Self-Healing Network Connectivity |
| **Algorithm** | BFS (detection) + DSU + Kruskal's (healing) |
| **Topologies Tested** | Watts-Strogatz, Barabási-Albert, Erdős-Rényi, Grid |
| **Failure Modes** | Random, Targeted (hub attack), Cascading |
| **Baselines** | Random edge activation, Degree-based heuristic |
| **Experiments** | 6 comprehensive experiments |
| **Key Result** | Full healing up to 30% failure · 36% cheaper than baselines |

---

## 📂 Project Structure

```
Adv_Graph_case_study/
│
├── self_healing_network.py    ← Core module (DSU, generators, healers, metrics)
├── experiments.py             ← 6 experiments with CSV + plot output
├── visualizations.py          ← Network diagrams, animation, heatmap
│
├── report.md                  ← Final report (structured by rubric criteria)
├── explain.md                 ← Detailed beginner-friendly explanation
├── README.md                  ← You are here
│
├── results/                   ← All generated outputs (19 files)
│   ├── exp1_failure_sweep.csv / .png
│   ├── exp2_topology_comparison.csv / .png
│   ├── exp3_scalability.csv / .png
│   ├── exp4_algorithm_comparison.csv / .png
│   ├── exp5_dormant_budget.csv / .png
│   ├── exp6_cascading.csv / .png
│   ├── three_panel_ws.png          ← Watts-Strogatz lifecycle
│   ├── three_panel_ba.png          ← Barabási-Albert targeted attack
│   ├── three_panel_cascading.png   ← Cascading failure scenario
│   ├── healing_animation.gif       ← Step-by-step healing animation
│   ├── metrics_heatmap.png         ← Cross-topology comparison
│   ├── adaptive_comparison.png     ← Static vs adaptive dormant pool
│   └── summary.txt
│
├── Adv_Graph_DA-1.pdf         ← DA-1 submission (problem definition)
└── graph_modelling.py         ← Original DA-1 prototype code
```

---

## 🚀 How to Run

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install networkx matplotlib numpy scipy pillow

# 3. Run core module (demo simulation + unit tests)
python3 self_healing_network.py

# 4. Run all 6 experiments (outputs CSVs + plots to results/)
python3 experiments.py

# 5. Generate all visualizations (outputs PNGs + GIF to results/)
python3 visualizations.py
```

All experiments use **`seed=42`** for full reproducibility — running twice gives identical results.

---

## 🧪 What Each File Does

### `self_healing_network.py` — Core Engine

The main module containing all algorithms and utilities:

| Component | Description |
|---|---|
| `class DSU` | Disjoint Set Union with path compression + union by rank |
| `generate_graph()` | Creates Watts-Strogatz / Barabási-Albert / Erdős-Rényi / Grid graphs |
| `generate_dormant_edges()` | Generates locality-aware backup edge pool (weighted by distance) |
| `simulate_failure()` | Removes nodes — random, targeted (highest-degree first), or cascading |
| `detect_partitions_bfs()` | BFS traversal to find disconnected components |
| `heal_kruskal_dsu()` | **Main algorithm** — greedy Kruskal's with DSU component tracking |
| `heal_random()` | Baseline 1 — random edge activation |
| `heal_degree_based()` | Baseline 2 — hub-first edge activation |
| `generate_adaptive_dormant()` | Innovation — dynamic backup edges near failure zones |
| `compute_metrics()` | Computes healing ratio, cost, components, diameter, etc. |
| `run_simulation()` | One-call pipeline: generate → fail → detect → heal → measure |

**When run directly:** Executes a demo simulation on WS(50 nodes, 15% failure) and runs DSU + BFS unit tests.

### `experiments.py` — Experimental Suite

Runs 6 experiments and saves results:

| # | Experiment | What It Tests |
|---|---|---|
| 1 | Failure Rate Sweep (5%–50%) | At what failure rate does healing degrade? |
| 2 | Topology Comparison | Which graph shape handles failures best/worst? |
| 3 | Scalability (50–500 nodes) | Does runtime stay practical at scale? |
| 4 | Algorithm Comparison | Is Kruskal-DSU better than baselines? |
| 5 | Dormant Budget (10%–60%) | How many backup edges are needed? |
| 6 | Cascading Failures (5 rounds) | Can the system survive sustained multi-round attacks? |

**Output:** 6 CSV files + 6 PNG charts in `results/`.

### `visualizations.py` — Figure Generation

| Output | Description |
|---|---|
| `three_panel_ws.png` | Initial → Failed → Healed (Watts-Strogatz, 30% random failure) |
| `three_panel_ba.png` | Initial → Failed → Healed (Barabási-Albert, 15% targeted attack) |
| `three_panel_cascading.png` | Cascading failure scenario |
| `healing_animation.gif` | Animated step-by-step healing (one edge per frame) |
| `metrics_heatmap.png` | Topology × failure mode metric comparison |
| `adaptive_comparison.png` | Static vs adaptive dormant pool side-by-side |

---

## 📊 Key Results Summary

### Healing works up to 30% failure, degrades beyond 35%
| Failure Rate | Components (Failed → Healed) | Healing Ratio |
|---|---|---|
| 5%–20% | 1 → 1 | 100% (no healing needed) |
| 25% | 2 → 1 | 100% |
| **30%** | **4 → 1** | **100%** |
| 35% | 5 → 2 | 75% |
| 50% | 9 → 4 | 63% |

### Kruskal-DSU is 36% cheaper than baselines
| Algorithm | Same Healing Ratio | Avg Cost |
|---|---|---|
| **Kruskal-DSU (ours)** | 91.7% | **18.2** |
| Random | 91.7% | 30.1 |
| Degree-Based | 91.7% | 29.5 |

### BA networks shatter under targeted attack
- 15% targeted failure on Barabási-Albert → **31 disconnected components**
- Our healer recovered 70% (31 → 3 components, activating 21 edges)

### Fast execution
- Healing phase: **<6ms at 500 nodes**
- Suitable for real-time network recovery

### Cascading failure resilience
- Sustained **3 rounds** of 10%/round cascading failure before dormant pool depletion

---

## 💡 Three Innovation Extensions

1. **Locality-Aware Healing** — Dormant edges weighted by Euclidean distance; Kruskal's naturally picks shorter/cheaper links → 36% cost reduction over random.

2. **Cascading Failure Simulation** — Multi-round failure where neighbors of failed nodes have 30% failure probability, modeling realistic domino-effect crashes.

3. **Adaptive Dormant Pool** — Dynamically generates emergency backup edges near failure zones (like deploying portable wireless bridges after a disaster).

---

## 📝 Report & Documentation

| File | Purpose |
|---|---|
| **[report.md](report.md)** | Final report organized by the 6 DA-II rubric criteria |
| **[explain.md](explain.md)** | Detailed explanation of every concept, algorithm, and result (beginner-friendly) |

The report includes a **Rubric Coverage Map** at the end showing exactly which sections address each grading criterion.

---

## ⚙️ Dependencies

| Package | Version | Purpose |
|---|---|---|
| `networkx` | 3.4.2 | Graph creation, algorithms, component detection |
| `matplotlib` | 3.10.8 | Plotting, visualization, animation |
| `numpy` | 2.2.6 | Numerical operations |
| `scipy` | 1.15.3 | Sparse matrix support for spring layout at scale |
| `pillow` | 12.2.0 | GIF animation export |

Python 3.10+

---

## 📎 DA-1 Reference

The DA-1 submission ([Adv_Graph_DA-1.pdf](Adv_Graph_DA-1.pdf)) defined:
- Graph modeling (G = (V, E) with active/dormant edges)
- Algorithm selection (BFS-DSU Hybrid) with justification
- Complexity analysis
- Literature review (Trehan 2012, Quattrociocchi 2014, Goyal 2025)

DA-2 implements, tests, and evaluates everything proposed in DA-1.
