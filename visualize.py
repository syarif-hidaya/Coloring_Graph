"""
visualize.py
============
Generates all visualizations for the lab practicum scheduling system,
with all rendered text (titles, axis labels, legends) in English:

1. Colored conflict graph (Greedy vs DSATUR) for a given level, with a
   legend mapping each color to its assigned time slot (day + slot
   number) and how many sessions were placed in that color group.
2. Bar/line charts comparing the number of colors (minimum) and
   execution time of Greedy vs DSATUR across all levels 1-5.
3. Weekly schedule heatmap (day x slot), where each cell is colored
   by its course (mata kuliah) rather than a plain occupied/empty
   color, with a legend mapping colors to course names.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import networkx as nx

from evaluate import evaluate_all_levels

PALETTE = plt.cm.tab20.colors

DAY_EN = {
    "Senin": "Monday",
    "Selasa": "Tuesday",
    "Rabu": "Wednesday",
    "Kamis": "Thursday",
    "Jumat": "Friday",
}


def _course_color_map(course_names):
    """Assign a consistent color to each unique course name, cycling
    through tab20 / tab20b / tab20c (60 distinct colors total)."""
    names = sorted(set(course_names))
    palette = list(plt.cm.tab20.colors) + list(plt.cm.tab20b.colors) + list(plt.cm.tab20c.colors)
    return {name: palette[i % len(palette)] for i, name in enumerate(names)}


def plot_colored_graphs(schedules, level, out_dir="output"):
    G = schedules[level]["G"]
    g_colors = schedules[level]["g_colors"]
    d_colors = schedules[level]["d_colors"]
    data = schedules[level]["data"]
    hari_list = data["hari"]
    slot_per_hari = data["slot_per_hari"]

    def slot_label(color):
        day = DAY_EN.get(hari_list[color // slot_per_hari], hari_list[color // slot_per_hari])
        slot = (color % slot_per_hari) + 1
        return f"{day} - Slot {slot}"

    pos = nx.spring_layout(G, seed=7, k=0.6)

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    for ax, colors, title in [
        (axes[0], g_colors, "Greedy Coloring (Sequential Order)"),
        (axes[1], d_colors, "DSATUR Coloring (Saturation Degree)"),
    ]:
        n_used = len(set(colors.values()))
        node_colors = [PALETTE[colors[n] % len(PALETTE)] for n in G.nodes()]
        nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.25, width=0.8)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                                node_size=260, edgecolors="black", linewidths=0.6)
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=6)
        ax.set_title(f"{title}\n{G.number_of_nodes()} sessions, {G.number_of_edges()} conflicts, "
                      f"{n_used} time slots used", fontsize=11)
        ax.axis("off")

        # legend: color -> assigned time slot + number of sessions in that color group
        counts = {}
        for n in colors:
            counts[colors[n]] = counts.get(colors[n], 0) + 1
        used_colors = sorted(counts.keys())
        handles = [mpatches.Patch(color=PALETTE[c % len(PALETTE)],
                                   label=f"{slot_label(c)} ({counts[c]} session{'s' if counts[c] != 1 else ''})")
                   for c in used_colors]
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.03),
                   ncol=3, fontsize=7, frameon=True, title="Color legend (time slot)")

    fig.suptitle(f"Conflict Graph Coloring Comparison — Level {level}",
                  fontsize=14, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(out_dir, f"graph_coloring_level{level}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_comparison_charts(df, out_dir="output"):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    levels = df["Level"]
    x = np.arange(len(levels))
    w = 0.35

    # Chart 1: minimum number of colors (chromatic estimate)
    ax = axes[0]
    b1 = ax.bar(x - w/2, df["Greedy - Warna Minimum"], w, label="Greedy Coloring", color="#e07a5f")
    b2 = ax.bar(x + w/2, df["DSATUR - Warna Minimum"], w, label="DSATUR Coloring", color="#3d5a80")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Level {l}" for l in levels])
    ax.set_ylabel("Minimum Number of Colors Required")
    ax.set_title("Compression Efficiency (Minimum Colors)")
    ax.legend()
    ax.bar_label(b1, fontsize=8)
    ax.bar_label(b2, fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    # Chart 2: execution time
    ax = axes[1]
    ax.plot(x, df["Greedy - Waktu (ms)"], marker="o", label="Greedy Coloring", color="#e07a5f")
    ax.plot(x, df["DSATUR - Waktu (ms)"], marker="s", label="DSATUR Coloring", color="#3d5a80")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Level {l}" for l in levels])
    ax.set_ylabel("Execution Time (ms)")
    ax.set_title("Algorithm Execution Time")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.suptitle("Algorithm Evaluation: Greedy Coloring vs DSATUR Coloring (Level 1-5)",
                  fontsize=14, fontweight="bold")
    fig.tight_layout()
    path = os.path.join(out_dir, "perbandingan_algoritma.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_schedule_heatmap(schedules, level, algo="dsatur", out_dir="output"):
    data = schedules[level]["data"]
    jadwal = schedules[level][f"jadwal_{algo}"]
    hari_list = data["hari"]
    slot_per_hari = data["slot_per_hari"]
    day_labels = [DAY_EN.get(h, h) for h in hari_list]

    all_courses = [s["mata_kuliah"] for s in data["sesi_praktikum"]]
    course_color = _course_color_map(all_courses)

    # group sessions that landed in the same (day, slot) cell
    cell_sessions = {}
    for s in jadwal:
        if s["slot"] == -1:
            continue
        r, c = s["slot"] - 1, hari_list.index(s["hari"])
        cell_sessions.setdefault((r, c), []).append(s["mata_kuliah"])

    fig, ax = plt.subplots(figsize=(10, 7.5))
    ax.set_xlim(-0.5, len(hari_list) - 0.5)
    ax.set_ylim(slot_per_hari - 0.5, -0.5)

    for r in range(slot_per_hari):
        for c in range(len(hari_list)):
            courses = cell_sessions.get((r, c), [])
            if not courses:
                ax.add_patch(mpatches.Rectangle((c - 0.5, r - 0.5), 1, 1,
                                                  facecolor="#f2f2f2", edgecolor="white"))
                continue
            # split the cell horizontally, one strip per parallel session
            n = len(courses)
            for i, course in enumerate(courses):
                x0 = c - 0.5 + i * (1.0 / n)
                ax.add_patch(mpatches.Rectangle((x0, r - 0.5), 1.0 / n, 1,
                                                  facecolor=course_color[course],
                                                  edgecolor="white", linewidth=0.6))
            label = courses[0][:12] + (f" +{n-1}" if n > 1 else "")
            ax.text(c, r, label, ha="center", va="center", fontsize=6.5,
                    color="black", fontweight="bold")

    ax.set_xticks(range(len(hari_list)))
    ax.set_xticklabels(day_labels, fontsize=10)
    ax.set_yticks(range(slot_per_hari))
    ax.set_yticklabels([f"Slot {i+1}" for i in range(slot_per_hari)], fontsize=9)
    ax.set_title(f"Weekly Schedule Heatmap — Level {level} "
                  f"({'DSATUR' if algo == 'dsatur' else 'Greedy'} Coloring)",
                  fontsize=12, fontweight="bold")
    ax.set_aspect("auto")
    for spine in ax.spines.values():
        spine.set_visible(False)

    # legend: course -> color, only for courses actually scheduled in this level
    scheduled_courses = sorted({c for courses in cell_sessions.values() for c in courses})
    handles = [mpatches.Patch(color=course_color[c], label=c) for c in scheduled_courses]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.06),
               ncol=4, fontsize=7, frameon=True, title="Course legend")

    fig.tight_layout()
    path = os.path.join(out_dir, f"heatmap_jadwal_level{level}_{algo}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


if __name__ == "__main__":
    df, schedules, csv_path = evaluate_all_levels()
    p1 = plot_colored_graphs(schedules, level=2)
    p2 = plot_comparison_charts(df)
    p3 = plot_schedule_heatmap(schedules, level=2, algo="dsatur")
    p4 = plot_schedule_heatmap(schedules, level=2, algo="greedy")
    print("Generated:", p1, p2, p3, p4, sep="\n- ")
