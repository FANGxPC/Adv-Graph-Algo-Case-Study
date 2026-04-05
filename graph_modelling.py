import networkx as nx
import matplotlib.pyplot as plt
import random
from matplotlib.animation import FuncAnimation
import copy

# ── 1. Graph with better visual properties ────────────────────────────────
n = 30
# Watts-Strogatz usually gives nicer spread than BA for visualization
G = nx.watts_strogatz_graph(n, k=2, p=0.18)     # avg degree ~3, good spread

# More dormant edges → more healing possible
dormant = set()
for u in range(n):
    for v in range(u + 1, n):
        if random.random() < 0.08 and not G.has_edge(u, v):   # ← increased to ~8%
            dormant.add((u, v))

# Better layout for readability (kamada_kawai usually clearer than spring)
pos = nx.kamada_kawai_layout(G)

# ── 2. More failures → more components → longer healing sequence ──────────
num_failures = 10   # ← increased (adjust 6–12 depending on n)
failed_nodes = random.sample(list(G.nodes()), num_failures)
G_fail = G.copy()
G_fail.remove_nodes_from(failed_nodes)

# ── 3. Improved greedy healing (try to pick "better" bridges) ─────────────
def simple_heal(graph, dormant_pool):
    healed = copy.deepcopy(graph)
    current_dormant = dormant_pool.copy()
    added_edges = []

    while not nx.is_connected(healed):
        components = list(nx.connected_components(healed))
        if len(components) < 2:
            break

        # Sort components by size (largest first)
        sorted_comps = sorted(components, key=len, reverse=True)
        comp1 = sorted_comps[0]

        # Try to connect to the second largest
        if len(sorted_comps) >= 2:
            comp2 = sorted_comps[1]
        else:
            break

        # Find bridge — prefer one with smallest "distance" in original pos
        best_bridge = None
        best_dist = float('inf')

        for u in comp1:
            for v in comp2:
                if (u, v) in current_dormant or (v, u) in current_dormant:
                    dist = sum((pos[u][i] - pos[v][i])**2 for i in (0,1)) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_bridge = (u, v)

        if best_bridge:
            healed.add_edge(*best_bridge)
            added_edges.append(best_bridge)
            current_dormant.discard(best_bridge)
            current_dormant.discard((best_bridge[1], best_bridge[0]))
        else:
            # fallback: any bridge
            for u in comp1:
                for v in comp2:
                    if (u, v) in current_dormant or (v, u) in current_dormant:
                        best_bridge = (u, v)
                        break
                if best_bridge: break
            if best_bridge:
                healed.add_edge(*best_bridge)
                added_edges.append(best_bridge)
                current_dormant.discard(best_bridge)
                current_dormant.discard((best_bridge[1], best_bridge[0]))
            else:
                break  # cannot connect anymore

    return healed, added_edges


# Run once for static image
G_healed, added_edges = simple_heal(G_fail, dormant)

# ── 4. Build animation steps (same logic) ─────────────────────────────────
healing_steps = [G_fail.copy()]
current_G = G_fail.copy()
current_dormant = dormant.copy()

while not nx.is_connected(current_G):
    components = list(nx.connected_components(current_G))
    if len(components) < 2:
        break

    sorted_comps = sorted(components, key=len, reverse=True)
    comp1 = sorted_comps[0]
    if len(sorted_comps) < 2:
        break
    comp2 = sorted_comps[1]

    best_bridge = None
    best_dist = float('inf')

    for u in comp1:
        for v in comp2:
            if (u, v) in current_dormant or (v, u) in current_dormant:
                dist = sum((pos.get(u, (0,0))[i] - pos.get(v, (0,0))[i])**2 for i in (0,1)) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_bridge = (u, v)

    if best_bridge:
        current_G.add_edge(*best_bridge)
        current_dormant.discard(best_bridge)
        current_dormant.discard((best_bridge[1], best_bridge[0]))
        healing_steps.append(current_G.copy())
    else:
        break

if len(healing_steps) == 1:
    healing_steps.append(healing_steps[0].copy())

# ── 5. Static figures (slightly tuned visuals) ────────────────────────────

plt.figure(figsize=(11, 9))
nx.draw_networkx_nodes(G, pos, node_size=260, node_color='lightblue')
nx.draw_networkx_edges(G, pos, edge_color='black', width=1.1, alpha=0.9)
nx.draw_networkx_edges(G, pos, edgelist=dormant, edge_color='gray', style='dashed', alpha=0.6, width=0.9)
nx.draw_networkx_labels(G, pos, font_size=8)
plt.title("Initial Network")
plt.axis('off')
plt.tight_layout()
plt.savefig("initial.png", dpi=300, bbox_inches='tight')
plt.close()

# Failed
plt.figure(figsize=(11, 9))
components = list(nx.connected_components(G_fail))
colors = plt.cm.tab10(range(len(components) + 2))
node_colors = [colors[i % len(colors)] for i, comp in enumerate(components) for _ in comp]
node_list = [n for comp in components for n in comp]
nx.draw_networkx_nodes(G_fail, pos, nodelist=node_list, node_color=node_colors, node_size=260)
nx.draw_networkx_edges(G_fail, pos, edge_color='black', width=1.1)
nx.draw_networkx_labels(G_fail, pos, font_size=8)
plt.title(f"After {num_failures} Node Failures")
plt.axis('off')
plt.tight_layout()
plt.savefig("failed.png", dpi=300, bbox_inches='tight')
plt.close()

# Healed
plt.figure(figsize=(11, 9))
nx.draw_networkx_nodes(G_healed, pos, node_size=260, node_color='lightgreen')
nx.draw_networkx_edges(G_healed, pos, edge_color='black', width=1.1)
if added_edges:
    nx.draw_networkx_edges(G_healed, pos, edgelist=added_edges, edge_color='red', width=2.8, style='solid')
nx.draw_networkx_labels(G_healed, pos, font_size=8)
plt.title(f"After Self-Healing ({len(added_edges)} edges added)")
plt.axis('off')
plt.tight_layout()
plt.savefig("healed.png", dpi=300, bbox_inches='tight')
plt.close()

# ── 6. Enhanced animation ─────────────────────────────────────────────────
def animate_healing():
    fig, ax = plt.subplots(figsize=(11, 9))

    def update(frame):
        ax.clear()
        curr = healing_steps[frame]
        nx.draw_networkx_nodes(curr, pos, nodelist=curr.nodes(),
                               node_color='lightblue', node_size=260, ax=ax)
        nx.draw_networkx_edges(curr, pos, edge_color='black', width=1.1, ax=ax)

        if frame > 0:
            prev = healing_steps[frame-1]
            new_edges = set(curr.edges()) - set(prev.edges())
            if new_edges:
                nx.draw_networkx_edges(curr, pos, edgelist=list(new_edges),
                                       edge_color='#d32f2f', width=4.0, style='solid', ax=ax)

        title = f"Step {frame+1}/{len(healing_steps)}   Components: {nx.number_connected_components(curr)}"
        if frame == len(healing_steps)-1:
            title += "  ✓ Connected"
        ax.set_title(title, fontsize=13)
        ax.axis('off')

    ani = FuncAnimation(fig, update, frames=range(len(healing_steps)),
                        interval=1800, repeat=True, repeat_delay=2000)
    ani.save("healing_animation.gif", writer='pillow', dpi=160)
    plt.close(fig)


animate_healing()

print("Done. Files created: initial.png  failed.png  healed.png  healing_animation.gif")
print(f"Healing steps shown: {len(healing_steps)}   New edges: {len(set(G_healed.edges()) - set(G_fail.edges()))}")