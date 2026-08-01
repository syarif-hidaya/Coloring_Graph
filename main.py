"""
main.py
=======
Entry point tunggal. Menjalankan seluruh pipeline:
1. Generate data random (level 1-5) -> data/data_level{n}.json
2. Bangun conflict graph & jalankan Greedy Coloring vs DSATUR Coloring
3. Hasilkan tabel evaluasi -> output/tabel_evaluasi.csv
4. Ekspor jadwal final (hasil DSATUR, algoritma terbaik) tiap level
   -> output/jadwal_level{n}.json dan .csv
5. Hasilkan visualisasi LENGKAP UNTUK SETIAP LEVEL (1-5):
   - output/graph_coloring_level{1..5}.png
   - output/heatmap_jadwal_level{1..5}_dsatur.png
   - output/heatmap_jadwal_level{1..5}_greedy.png
   - output/perbandingan_algoritma.png (ringkasan semua level sekaligus)

Cara pakai:
    python3 main.py
"""

import os
import json
import pandas as pd

from data_generator import generate_all_levels
from evaluate import evaluate_all_levels
from visualize import plot_colored_graphs, plot_comparison_charts, plot_schedule_heatmap

DATA_DIR = "data"
OUT_DIR = "output"
ALL_LEVELS = range(1, 6)  # visualisasi dibuat untuk seluruh level 1-5


def export_schedules(schedules, out_dir=OUT_DIR):
    for level, s in schedules.items():
        jadwal = s["jadwal_dsatur"]  # gunakan hasil algoritma terbaik (DSATUR)
        with open(os.path.join(out_dir, f"jadwal_level{level}.json"), "w", encoding="utf-8") as f:
            json.dump(jadwal, f, ensure_ascii=False, indent=2)
        pd.DataFrame(jadwal).to_csv(os.path.join(out_dir, f"jadwal_level{level}.csv"), index=False)


def main():
    print("=" * 70)
    print("PIPELINE PENJADWALAN PRAKTIKUM - GRAPH COLORING vs GREEDY COLORING")
    print("=" * 70)

    print("\n[1/4] Generating random data (level 1-5)...")
    generate_all_levels(out_dir=DATA_DIR)

    print("\n[2/4] Menjalankan & mengevaluasi algoritma di semua level...")
    df, schedules, csv_path = evaluate_all_levels(data_dir=DATA_DIR, out_dir=OUT_DIR)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", None)
    print(df.to_string(index=False))

    print("\n[3/4] Mengekspor jadwal final (DSATUR) per level...")
    export_schedules(schedules, out_dir=OUT_DIR)

    print("\n[4/4] Membuat visualisasi untuk SEMUA level (1-5)...")
    generated = []
    for level in ALL_LEVELS:
        p1 = plot_colored_graphs(schedules, level=level, out_dir=OUT_DIR)
        p2 = plot_schedule_heatmap(schedules, level=level, algo="dsatur", out_dir=OUT_DIR)
        p3 = plot_schedule_heatmap(schedules, level=level, algo="greedy", out_dir=OUT_DIR)
        generated += [p1, p2, p3]
        print(f"  Level {level}: {os.path.basename(p1)}, {os.path.basename(p2)}, {os.path.basename(p3)}")

    p_compare = plot_comparison_charts(df, out_dir=OUT_DIR)
    generated.append(p_compare)

    print("\nSemua file output:")
    for f in sorted(os.listdir(OUT_DIR)):
        print(f"  - {os.path.join(OUT_DIR, f)}")

    print("\nSELESAI.")


if __name__ == "__main__":
    main()

