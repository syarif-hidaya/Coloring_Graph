"""
scheduler.py
============
Inti sistem penjadwalan praktikum berbasis GRAPH COLORING.

Model masalah:
- Setiap sesi praktikum = 1 node/simpul graph.
- Dua sesi diberi EDGE (konflik) jika mereka berbagi sumber daya yang
  sama (dosen, asisten, ruang lab, atau peralatan lab) -> tidak boleh
  dijadwalkan pada slot waktu yang sama.
- Slot waktu (Senin-Jumat x 10 slot/hari = 50 slot) dipetakan sebagai
  "warna" (color) pada graph coloring. Sesi dengan warna sama = slot
  waktu sama, sehingga syarat graph coloring (simpul bertetangga tidak
  boleh warna sama) otomatis menjamin sesi yang bentrok sumber daya
  tidak dijadwalkan bersamaan.
- Tujuan: meminimalkan jumlah warna (slot waktu unik) yang dipakai,
  yaitu proper coloring dengan chromatic number sekecil mungkin.

CATATAN: field "inventaris_lab" (aset tetap ruang lab dengan tag RFID,
lihat data_generator.py) SENGAJA TIDAK dibaca oleh build_conflict_graph()
di bawah -- aset ini bukan sumber daya yang diperebutkan antar sesi,
jadi tidak mempengaruhi pembuatan edge/konflik maupun hasil coloring.
Field ini hanya ditempelkan (join) ke tiap baris jadwal akhir sebagai
informasi aset ruang, lihat map_colors_to_schedule() dan
distribute_full_schedule().

Dua algoritma dibandingkan:
1. Greedy Coloring biasa (urutan alami / sequential order) - via
   networkx strategy 'connected_sequential' (setara node-by-node,
   insertion order, tanpa strategi pengurutan cerdas).
2. DSATUR (Degree of Saturation) - algoritma graph coloring yang
   lebih canggih: pada tiap langkah memilih simpul dengan "saturation
   degree" tertinggi (jumlah warna berbeda pada tetangga), dan jika
   seri, pilih derajat tertinggi. Dikenal menghasilkan jumlah warna
   yang jauh lebih efisien/mendekati optimal dibanding greedy naif.
   Diimplementasikan manual (networkx tidak menyediakan DSATUR asli
   sebagai fungsi terpisah, hanya strategi 'saturation_largest_first'
   yang mirip tapi tanpa update saturasi dinamis penuh; di sini kita
   implementasikan DSATUR asli dari algoritma Brelaz 1979).
"""

import json
import time
import itertools
import networkx as nx


# ---------------------------------------------------------------------
# 1. Membangun conflict graph dari data sesi praktikum
# ---------------------------------------------------------------------
def build_conflict_graph(data: dict) -> nx.Graph:
    sesi_list = data["sesi_praktikum"]
    G = nx.Graph()
    for sesi in sesi_list:
        G.add_node(sesi["id_sesi"], **sesi)

    for a, b in itertools.combinations(sesi_list, 2):
        konflik = (
            a["dosen"] == b["dosen"]
            or a["ruang_lab"] == b["ruang_lab"]
            or bool(set(a["asisten"]) & set(b["asisten"]))
            or bool(set(a["peralatan_lab"]) & set(b["peralatan_lab"]))
        )
        if konflik:
            G.add_edge(a["id_sesi"], b["id_sesi"])
    return G


# ---------------------------------------------------------------------
# 2. Algoritma 1: Greedy Coloring biasa (sequential, urutan alami)
# ---------------------------------------------------------------------
def greedy_coloring(G: nx.Graph):
    """Greedy coloring naif: proses node sesuai urutan insersi graph,
    berikan warna terkecil yang belum dipakai tetangga yang sudah
    diwarnai. Tidak ada strategi pengurutan pintar."""
    t0 = time.perf_counter()
    order = list(G.nodes())  # urutan alami / insersi, TANPA sorting cerdas
    color_of = {}
    for node in order:
        used = {color_of[n] for n in G.neighbors(node) if n in color_of}
        c = 0
        while c in used:
            c += 1
        color_of[node] = c
    elapsed = time.perf_counter() - t0
    n_colors = len(set(color_of.values()))
    return color_of, n_colors, elapsed


# ---------------------------------------------------------------------
# 3. Algoritma 2: DSATUR (Degree of Saturation, Brelaz 1979)
# ---------------------------------------------------------------------
def dsatur_coloring(G: nx.Graph):
    """DSATUR: pada tiap iterasi pilih node belum berwarna dengan
    saturation degree (banyak warna berbeda di tetangga) tertinggi;
    jika seri, pilih derajat (degree) tertinggi. Lebih adaptif
    daripada greedy urutan tetap sehingga umumnya memakai warna lebih
    sedikit / lebih dekat ke chromatic number optimal."""
    t0 = time.perf_counter()
    color_of = {}
    degree = dict(G.degree())
    saturation = {n: set() for n in G.nodes()}
    uncolored = set(G.nodes())

    while uncolored:
        # pilih node dengan saturasi tertinggi, tie-break derajat tertinggi
        node = max(uncolored, key=lambda n: (len(saturation[n]), degree[n]))
        used = {color_of[nb] for nb in G.neighbors(node) if nb in color_of}
        c = 0
        while c in used:
            c += 1
        color_of[node] = c
        uncolored.remove(node)
        for nb in G.neighbors(node):
            if nb in uncolored:
                saturation[nb].add(c)

    elapsed = time.perf_counter() - t0
    n_colors = len(set(color_of.values()))
    return color_of, n_colors, elapsed


# ---------------------------------------------------------------------
# 4. Memetakan warna -> jadwal (hari, slot)
# ---------------------------------------------------------------------
def _inventaris_ruang(data: dict, ruang: str) -> list:
    """Ambil daftar aset tetap (RFID) milik sebuah ruang lab, jika ada.
    Field ini HANYA informasi tambahan pada output jadwal -- TIDAK
    pernah dibaca oleh build_conflict_graph() sehingga tidak mempengaruhi
    hasil penjadwalan sama sekali."""
    return data.get("sumber_daya", {}).get("inventaris_lab", {}).get(ruang, [])


def map_colors_to_schedule(color_of: dict, data: dict):
    hari_list = data["hari"]
    slot_per_hari = data["slot_per_hari"]
    total_slot = len(hari_list) * slot_per_hari

    max_color = max(color_of.values())
    feasible = (max_color + 1) <= total_slot

    jadwal = []
    sesi_by_id = {s["id_sesi"]: s for s in data["sesi_praktikum"]}
    for id_sesi, color in color_of.items():
        if color >= total_slot:
            hari, slot = "TIDAK MUAT", -1
        else:
            hari = hari_list[color // slot_per_hari]
            slot = (color % slot_per_hari) + 1
        sesi = sesi_by_id[id_sesi]
        jadwal.append({
            "id_sesi": id_sesi,
            "mata_kuliah": sesi["mata_kuliah"],
            "kelas": sesi["kelas"],
            "dosen": sesi["dosen"],
            "asisten": sesi["asisten"],
            "ruang_lab": sesi["ruang_lab"],
            "peralatan_lab": sesi["peralatan_lab"],
            "inventaris_ruang_lab": _inventaris_ruang(data, sesi["ruang_lab"]),
            "hari": hari,
            "slot": slot,
            "warna_graph": color,
        })
    jadwal.sort(key=lambda x: (hari_list.index(x["hari"]) if x["hari"] in hari_list else 99, x["slot"]))
    return jadwal, feasible


# ---------------------------------------------------------------------
# 4b. Distribusi PENUH ke seluruh slot (revisi: Senin-Jumat harus penuh)
# ---------------------------------------------------------------------
def distribute_full_schedule(color_of: dict, data: dict):
    """map_colors_to_schedule() di atas memetakan warna->slot secara
    LANGSUNG (warna 0 -> slot pertama, dst), sehingga jika algoritma
    coloring hanya butuh k warna (k jauh lebih kecil dari 50 slot yang
    tersedia -- ini WAJAR karena tujuan graph coloring memang memampatkan
    sesi ke slot sesedikit mungkin), maka slot ke-(k+1) s.d. ke-50 akan
    kosong sama sekali.

    Fungsi ini menyebarkan (redistribute) sesi hasil coloring ke SELURUH
    50 slot secara proporsional per kelompok warna, sehingga jadwal
    akhir Senin-Jumat terisi penuh. Ini TETAP AMAN secara constraint:
    - Sesi dalam kelompok warna yang SAMA sudah terbukti tidak saling
      bentrok (independent set hasil proper coloring), sehingga boleh
      dipecah dan disebar ke slot manapun tanpa risiko bentrok baru.
    - Sesi dari kelompok warna BERBEDA tidak pernah digabung ke slot
      yang sama, sehingga tidak ada bentrok sumber daya yang muncul.

    Jumlah slot yang dialokasikan untuk tiap kelompok warna sebanding
    dengan jumlah sesi pada kelompok tsb (metode largest remainder),
    minimum 1 slot per kelompok, dan totalnya persis = total_slot.
    """
    hari_list = data["hari"]
    slot_per_hari = data["slot_per_hari"]
    total_slot = len(hari_list) * slot_per_hari

    groups = {}
    for id_sesi, c in color_of.items():
        groups.setdefault(c, []).append(id_sesi)
    colors_sorted = sorted(groups.keys())
    k = len(colors_sorted)
    n = len(color_of)

    feasible = k <= total_slot and n <= total_slot * 50  # batas akal sehat

    if k == 0:
        return [], True, 0

    if k > total_slot:
        # Terlalu banyak warna dibanding slot tersedia -> tidak feasible;
        # fallback: pakai mapping langsung (akan menandai TIDAK MUAT).
        return map_colors_to_schedule(color_of, data)

    # --- alokasi jumlah slot per kelompok, proporsional terhadap ukuran
    #     kelompok, DIBATASI maksimum = jumlah sesi pada kelompok tsb
    #     (sebuah kelompok tidak mungkin mengisi lebih banyak slot unik
    #     daripada jumlah sesi yang dimilikinya, atau akan ada slot
    #     kosong yang "dijatah" tapi tak terisi sesi apapun). Karena
    #     total sesi n >= total_slot (dijamin oleh data_generator),
    #     total kapasitas seluruh kelompok selalu cukup untuk mengisi
    #     semua slot.
    sizes = [len(groups[c]) for c in colors_sorted]
    exact = [s / n * total_slot for s in sizes]
    alloc = [min(sizes[i], max(1, int(exact[i]))) for i in range(k)]
    remaining = total_slot - sum(alloc)
    # sisa slot dibagikan bergiliran ke kelompok yang masih punya "kapasitas"
    # (alloc < sizes), berputar sampai persis total_slot terisi
    guard = 0
    while remaining > 0 and guard < 100000:
        idx = guard % k
        if alloc[idx] < sizes[idx]:
            alloc[idx] += 1
            remaining -= 1
        guard += 1

    # --- assign slot spesifik ke tiap sesi (round-robin dalam kelompoknya) ---
    sesi_by_id = {s["id_sesi"]: s for s in data["sesi_praktikum"]}
    jadwal = []
    slot_cursor = 0
    for gi, c in enumerate(colors_sorted):
        n_slot_grup = alloc[gi]
        target_slots = list(range(slot_cursor, slot_cursor + n_slot_grup))
        slot_cursor += n_slot_grup
        anggota = groups[c]
        for idx_s, id_sesi in enumerate(anggota):
            slot_idx = target_slots[idx_s % len(target_slots)]
            hari = hari_list[slot_idx // slot_per_hari]
            slot = (slot_idx % slot_per_hari) + 1
            sesi = sesi_by_id[id_sesi]
            jadwal.append({
                "id_sesi": id_sesi,
                "mata_kuliah": sesi["mata_kuliah"],
                "kelas": sesi["kelas"],
                "dosen": sesi["dosen"],
                "asisten": sesi["asisten"],
                "ruang_lab": sesi["ruang_lab"],
                "peralatan_lab": sesi["peralatan_lab"],
                "inventaris_ruang_lab": _inventaris_ruang(data, sesi["ruang_lab"]),
                "hari": hari,
                "slot": slot,
                "warna_graph": c,
            })

    jadwal.sort(key=lambda x: (hari_list.index(x["hari"]), x["slot"]))
    slot_terisi = len({(s["hari"], s["slot"]) for s in jadwal})
    return jadwal, feasible, slot_terisi


# ---------------------------------------------------------------------
# 5. Validasi: pastikan tidak ada bentrok sumber daya pada jadwal akhir
# ---------------------------------------------------------------------
def validate_schedule(jadwal: list) -> int:
    """Menghitung jumlah pelanggaran (dua sesi beda id, sama hari+slot,
    berbagi sumber daya). Idealnya = 0 jika coloring valid."""
    violations = 0
    by_slot = {}
    for s in jadwal:
        key = (s["hari"], s["slot"])
        by_slot.setdefault(key, []).append(s)
    for key, sesi_sama_slot in by_slot.items():
        for a, b in itertools.combinations(sesi_sama_slot, 2):
            if (a["dosen"] == b["dosen"] or a["ruang_lab"] == b["ruang_lab"]
                    or set(a["asisten"]) & set(b["asisten"])
                    or set(a["peralatan_lab"]) & set(b["peralatan_lab"])):
                violations += 1
    return violations


if __name__ == "__main__":
    with open("data/data_level3.json", encoding="utf-8") as f:
        data = json.load(f)
    G = build_conflict_graph(data)
    print(f"Level 3: {G.number_of_nodes()} node, {G.number_of_edges()} edge")

    for name, fn in [("Greedy", greedy_coloring), ("DSATUR", dsatur_coloring)]:
        colors, n_colors, t = fn(G)
        jadwal, feasible = map_colors_to_schedule(colors, data)
        v = validate_schedule(jadwal)
        print(f"{name}: {n_colors} warna, {t*1000:.3f} ms, feasible={feasible}, violations={v}")
