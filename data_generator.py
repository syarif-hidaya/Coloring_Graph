"""
data_generator.py
==================
Generator data random untuk sistem penjadwalan praktikum.
Menghasilkan data dosen, asisten, ruang lab, peralatan lab, dan
daftar sesi praktikum yang perlu dijadwalkan, dalam 5 tingkat
kesulitan (level 1 = ringan, level 5 = berat/padat konflik).

Setiap sesi praktikum membutuhkan:
- 1 dosen pengampu
- 1-2 asisten praktikum
- 1 ruang lab
- 1-3 unit peralatan lab (portable, ikut menentukan konflik/jadwal)

Selain itu, tiap RUANG LAB memiliki inventaris ASET TETAP (proyektor, PC,
dsb) yang masing-masing diberi tag RFID. Aset tetap ini murni informasi
properti ruang -- TIDAK dipakai untuk menghitung konflik/penjadwalan --
namun disertakan pada hasil jadwal akhir (lihat scheduler.py) supaya
diketahui aset apa saja yang tersedia di ruang tempat sesi berlangsung.

Semakin tinggi level, semakin banyak sesi tetapi jumlah pool
sumber daya (dosen/asisten/ruang/alat) relatif tidak bertambah
secepat jumlah sesi -> kepadatan konflik (graph density) naik.

Output: file JSON per level di folder data/ (data_level{n}.json)
"""

import json
import random
import os

MATA_KULIAH = [
    "Algoritma & Pemrograman", "Basis Data", "Jaringan Komputer",
    "Sistem Operasi", "Kecerdasan Buatan", "Pemrograman Web",
    "Struktur Data", "Sistem Digital", "Mikrokontroler", "IoT",
    "Machine Learning", "Grafika Komputer", "Keamanan Jaringan",
    "Sistem Tertanam", "Rekayasa Perangkat Lunak", "Data Mining",
    "Pemrograman Mobile", "Robotika", "Komputasi Awan", "Multimedia"
]

NAMA_DEPAN = ["Adi", "Budi", "Citra", "Dewi", "Eka", "Farhan", "Gita",
              "Hadi", "Indah", "Joko", "Kartika", "Lutfi", "Maya",
              "Nanda", "Oka", "Putri", "Rama", "Sari", "Taufik", "Umi",
              "Vina", "Wira", "Yoga", "Zahra"]

GELAR = ["S.T., M.T.", "S.Kom., M.Kom.", "M.Eng.", "Ph.D.", "M.Cs."]

# Aset TETAP milik ruang laboratorium (bukan peralatan portable per sesi
# praktikum di atas). Setiap unit diberi tag RFID. Aset ini TIDAK dipakai
# untuk membangun conflict graph / menentukan penjadwalan -- hanya
# informasi inventaris ruang yang disertakan pada hasil jadwal akhir.
ASET_TETAP_LAB = [
    "Proyektor", "Layar Proyeksi", "PC Desktop Praktikum", "Access Point WiFi",
    "Switch Jaringan", "Router", "Papan Tulis Digital", "AC (Pendingin Ruangan)",
    "Server Rack", "UPS", "Kamera CCTV", "Printer 3D", "Osiloskop",
    "Modul Praktikum IoT", "Rak Peralatan", "Sound System", "Meja Kerja Lab",
    "Kabel Jaringan Terpasang", "Panel Listrik", "Whiteboard",
]

KONDISI_ASET = ["Baik", "Baik", "Baik", "Baik", "Perlu Perbaikan", "Dalam Perawatan"]

# CATATAN REVISI: total slot yang tersedia dalam seminggu adalah
# 5 hari x 10 slot = 50 slot. Agar jadwal Senin-Jumat bisa PENUH
# (semua 50 slot terisi) di setiap level, jumlah sesi (n_sesi) HARUS
# >= 50 -- sebab tidak mungkin mengisi 50 slot dengan sesi yang lebih
# sedikit dari itu. Level tetap dibedakan tingkat kesulitannya lewat
# rasio sesi terhadap pool sumber daya (semakin tinggi level, pool
# semakin sempit relatif terhadap jumlah sesi -> makin padat konflik),
# namun n_sesi kini selalu >= total_slot (50) di semua level.
LEVEL_CONFIG = {
    1: dict(n_sesi=50,  n_dosen=14, n_asisten=20, n_ruang=8,  n_alat=14),
    2: dict(n_sesi=65,  n_dosen=15, n_asisten=22, n_ruang=8,  n_alat=15),
    3: dict(n_sesi=80,  n_dosen=16, n_asisten=24, n_ruang=9,  n_alat=16),
    4: dict(n_sesi=95,  n_dosen=17, n_asisten=26, n_ruang=9,  n_alat=17),
    5: dict(n_sesi=110, n_dosen=18, n_asisten=28, n_ruang=10, n_alat=18),
}


def _buat_nama(prefix, idx):
    nama = random.choice(NAMA_DEPAN)
    return f"{prefix}-{idx:02d} ({nama} {random.choice(GELAR) if prefix=='D' else ''})".strip()


def _buat_rfid() -> str:
    """Menghasilkan nomor tag RFID acak, format mirip EPC (24 digit hex)
    dengan prefix agar mudah dikenali sebagai aset lab."""
    return "RFID-" + "".join(random.choices("0123456789ABCDEF", k=12))


def generate_inventaris_lab(ruang_list: list) -> dict:
    """Generate inventaris ASET TETAP untuk tiap ruang lab, masing-masing
    diberi tag RFID unik. Ini adalah properti ruang (fixed asset), bukan
    peralatan yang dipesan per sesi -- sehingga TIDAK ikut dipakai dalam
    pengecekan konflik/penjadwalan (lihat scheduler.py: build_conflict_graph
    tidak membaca field ini sama sekali). Hasilnya hanya disertakan pada
    output jadwal akhir sebagai informasi aset di ruang tempat sesi
    berlangsung."""
    inventaris = {}
    for ruang in ruang_list:
        n_item = random.randint(4, 8)
        n_item = min(n_item, len(ASET_TETAP_LAB))
        item_terpilih = random.sample(ASET_TETAP_LAB, k=n_item)
        inventaris[ruang] = [
            {
                "nama_alat": item,
                "rfid": _buat_rfid(),
                "kondisi": random.choice(KONDISI_ASET),
            }
            for item in item_terpilih
        ]
    return inventaris


def generate_level_data(level: int, seed: int = None) -> dict:
    if level not in LEVEL_CONFIG:
        raise ValueError("Level harus 1-5")
    if seed is not None:
        random.seed(seed)

    cfg = LEVEL_CONFIG[level]

    dosen = [f"Dr. {random.choice(NAMA_DEPAN)} {random.choice(GELAR)} (D{idx+1:02d})"
              for idx in range(cfg["n_dosen"])]
    asisten = [f"{random.choice(NAMA_DEPAN)} (A{idx+1:02d})"
               for idx in range(cfg["n_asisten"])]
    ruang = [f"Lab-{chr(65+idx)}" for idx in range(cfg["n_ruang"])]
    alat = [f"Alat-{idx+1:02d}" for idx in range(cfg["n_alat"])]
    inventaris_lab = generate_inventaris_lab(ruang)

    sesi_list = []
    for i in range(cfg["n_sesi"]):
        matkul = random.choice(MATA_KULIAH)
        n_asisten_sesi = random.randint(1, 2)
        n_alat_sesi = random.randint(1, 3)
        sesi = {
            "id_sesi": f"L{level}-S{i+1:03d}",
            "mata_kuliah": matkul,
            "kelas": random.choice(["A", "B", "C"]),
            "dosen": random.choice(dosen),
            "asisten": sorted(random.sample(asisten, k=n_asisten_sesi)),
            "ruang_lab": random.choice(ruang),
            "peralatan_lab": sorted(random.sample(alat, k=n_alat_sesi)),
            "durasi_slot": 1,  # dalam satuan slot (1 slot = 1 sesi praktikum)
        }
        sesi_list.append(sesi)

    data = {
        "level": level,
        "deskripsi_level": {
            1: "Ringan - sedikit sesi, sumber daya longgar",
            2: "Sedang-ringan",
            3: "Sedang",
            4: "Sedang-berat",
            5: "Berat - banyak sesi, sumber daya padat/terbatas",
        }[level],
        "hari": ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"],
        "slot_per_hari": 10,
        "total_slot_tersedia": 5 * 10,
        "sumber_daya": {
            "dosen": dosen,
            "asisten": asisten,
            "ruang_lab": ruang,
            "peralatan_lab": alat,
            "inventaris_lab": inventaris_lab,
        },
        "sesi_praktikum": sesi_list,
    }
    return data


def generate_all_levels(out_dir="data", seed_base=42):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for level in range(1, 6):
        data = generate_level_data(level, seed=seed_base + level)
        path = os.path.join(out_dir, f"data_level{level}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        paths.append(path)
        print(f"[OK] Level {level}: {len(data['sesi_praktikum'])} sesi -> {path}")
    return paths


if __name__ == "__main__":
    generate_all_levels()
