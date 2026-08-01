"""
evaluate.py
===========
Menjalankan kedua algoritma (Greedy Coloring vs DSATUR Coloring) pada
data level 1-5, mengumpulkan metrik evaluasi, dan menghasilkan tabel
perbandingan (CSV + tampilan konsol).

Metrik yang diukur:
- Jumlah node (sesi) & edge (pasangan konflik) & densitas graph
- Jumlah warna (slot waktu unik) yang dipakai tiap algoritma
- Waktu eksekusi (ms) tiap algoritma
- Feasible atau tidak (apakah muat dalam 50 slot yang tersedia)
- Jumlah pelanggaran (violations) pada jadwal akhir -> validasi
- Efisiensi DSATUR terhadap Greedy (persentase pengurangan warna)
"""

import json
import os
import pandas as pd

from scheduler import (
    build_conflict_graph, greedy_coloring, dsatur_coloring,
    map_colors_to_schedule, distribute_full_schedule, validate_schedule,
)


def evaluate_all_levels(data_dir="data", out_dir="output"):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    schedules = {}  # level -> (jadwal_greedy, jadwal_dsatur, G)

    for level in range(1, 6):
        with open(os.path.join(data_dir, f"data_level{level}.json"), encoding="utf-8") as f:
            data = json.load(f)

        G = build_conflict_graph(data)
        n_node = G.number_of_nodes()
        n_edge = G.number_of_edges()
        max_edge = n_node * (n_node - 1) / 2
        density = n_edge / max_edge if max_edge > 0 else 0

        g_colors, g_n, g_t = greedy_coloring(G)
        d_colors, d_n, d_t = dsatur_coloring(G)

        # jadwal akhir yang diekspor/divisualisasikan: disebar ke SELURUH
        # 50 slot (Senin-Jumat penuh), bukan dipadatkan ke jumlah warna
        # minimum -- lihat distribute_full_schedule() di scheduler.py
        jadwal_g, feas_g, terisi_g = distribute_full_schedule(g_colors, data)
        jadwal_d, feas_d, terisi_d = distribute_full_schedule(d_colors, data)

        v_g = validate_schedule(jadwal_g)
        v_d = validate_schedule(jadwal_d)

        total_slot = data["total_slot_tersedia"]
        reduksi = (g_n - d_n) / g_n * 100 if g_n > 0 else 0

        rows.append({
            "Level": level,
            "Jumlah Sesi (Node)": n_node,
            "Jumlah Konflik (Edge)": n_edge,
            "Densitas Graph": round(density, 3),
            "Greedy - Warna Minimum": g_n,
            "Greedy - Waktu (ms)": round(g_t * 1000, 4),
            "Greedy - Slot Terisi": f"{terisi_g}/{total_slot}",
            "Greedy - Pelanggaran": v_g,
            "DSATUR - Warna Minimum": d_n,
            "DSATUR - Waktu (ms)": round(d_t * 1000, 4),
            "DSATUR - Slot Terisi": f"{terisi_d}/{total_slot}",
            "DSATUR - Pelanggaran": v_d,
            "Efisiensi DSATUR (%)": round(reduksi, 2),
        })

        schedules[level] = dict(G=G, jadwal_greedy=jadwal_g, jadwal_dsatur=jadwal_d,
                                 g_colors=g_colors, d_colors=d_colors, data=data)

    df = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, "tabel_evaluasi.csv")
    df.to_csv(csv_path, index=False)
    return df, schedules, csv_path


if __name__ == "__main__":
    df, schedules, csv_path = evaluate_all_levels()
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", None)
    print(df.to_string(index=False))
    print(f"\n[OK] Tabel evaluasi disimpan di: {csv_path}")
