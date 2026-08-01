# Editor Jadwal Praktikum (PHP + HTML + JS)

Antarmuka web untuk menampilkan hasil jadwal praktikum (`jadwal_level{n}.json`
dari sistem Python `lab_scheduling`), dengan fitur **drag & drop** untuk
menggeser sesi ke slot lain secara manual, lalu **menyimpan** hasilnya
kembali ke file JSON (dan CSV pendamping) di server.

## Struktur Proyek

```
web_schedule_editor/
├── index.php           # halaman utama (grid jadwal)
├── api.php             # backend: load & save data jadwal (JSON)
├── assets/
│   ├── style.css
│   └── app.js
└── data/
    ├── jadwal_level1.json ... jadwal_level5.json   (hasil jadwal — DIBACA & DITULIS)
    ├── data_level1.json ... data_level5.json        (opsional, hanya untuk metadata hari/slot)
    └── backup/                                       (dibuat otomatis saat menyimpan)
```

## Kebutuhan

- PHP 7.4+ (diuji dengan PHP 8.3), tidak butuh database maupun ekstensi tambahan.
- Browser modern (drag & drop native HTML5).

## Cara Menjalankan

### 1. Server bawaan PHP (paling cepat, untuk coba-coba lokal)
```bash
cd web_schedule_editor
php -S localhost:8000
```
Buka `http://localhost:8000` di browser.

### 2. Apache / Nginx + PHP-FPM (produksi)
Salin folder `web_schedule_editor/` ke document root server (mis.
`/var/www/html/jadwal/`), pastikan folder `data/` dan `data/backup/`
dapat ditulis oleh user web server:
```bash
chmod -R 775 data/
```
Lalu akses `http://<domain-atau-ip>/jadwal/`.

### 3. XAMPP/Laragon (Windows, umum dipakai di lingkungan kampus)
Salin folder `web_schedule_editor/` ke `htdocs/`, jalankan Apache dari
control panel, akses `http://localhost/web_schedule_editor/`.

## Cara Pakai

1. Pilih **Level** di pojok kanan atas — grid Senin–Jumat x 10 slot akan
   dimuat berisi kartu-kartu sesi (mata kuliah, dosen, ruang) sesuai
   `jadwal_level{n}.json`.
2. **Seret (drag)** kartu sesi ke sel hari/slot lain untuk menggeser
   jadwalnya secara manual.
3. Jika hasil geseran membuat satu slot berisi >1 sesi yang berbagi
   dosen/asisten/ruang/alat yang sama, sel tsb otomatis ditandai
   **merah** (peringatan bentrok) — ini hanya peringatan visual, Anda
   tetap bebas menyimpan susunan apapun.
4. Klik kartu sesi untuk melihat **detail lengkap** (dosen, asisten,
   ruang, peralatan portable, serta inventaris tetap ruang + nomor RFID).
5. Klik **💾 Simpan Perubahan** untuk menulis susunan baru kembali ke
   `data/jadwal_level{n}.json` dan `.csv` di server. Sebuah salinan
   cadangan otomatis dibuat di `data/backup/` sebelum file lama ditimpa.
6. **⟳ Muat Ulang** membaca ulang file dari server (perubahan yang
   belum disimpan akan hilang — akan ada konfirmasi terlebih dahulu).

## Cara Kerja Backend (`api.php`)

| Endpoint | Method | Fungsi |
|---|---|---|
| `api.php?action=levels` | GET | Daftar level yang terdeteksi (scan `data/jadwal_level*.json`) |
| `api.php?action=load&level=N` | GET | Ambil isi jadwal level N + metadata hari/slot |
| `api.php?action=save&level=N` | POST (body: array JSON sesi) | Timpa `jadwal_level{N}.json` & `.csv`, buat backup otomatis |

**Penting:** peralatan tetap ruang (`inventaris_ruang_lab`, dengan RFID)
maupun peralatan portable (`peralatan_lab`) hanya ditampilkan/diteruskan
apa adanya oleh backend — **tidak** ikut divalidasi ulang terhadap
conflict graph Python. Deteksi bentrok di antarmuka ini murni
peringatan visual sisi klien (JavaScript), bukan validasi otoritatif.
Jika Anda menggeser sesi ke slot yang bentrok dan menyimpannya, sistem
akan tetap menyimpannya — silakan gunakan indikator merah sebagai
panduan sebelum menyimpan.

## Menambah / Memperbarui Data

Untuk memuat hasil terbaru dari pipeline Python, cukup salin ulang file
`output/jadwal_level*.json` (dan `data/data_level*.json` untuk metadata)
dari proyek `lab_scheduling` ke folder `data/` editor ini — timpa file
lama. Level baru (mis. Level 6) akan otomatis muncul di dropdown selama
namanya mengikuti pola `jadwal_level{n}.json`.
