<?php
/**
 * api.php
 * =======
 * Backend sederhana untuk Editor Jadwal Praktikum.
 *
 * Endpoint (semua lewat query string ?action=...):
 *   GET  api.php?action=levels
 *       -> daftar level yang tersedia (mendeteksi file data/jadwal_level{n}.json)
 *
 *   GET  api.php?action=load&level=N
 *       -> isi jadwal level N (array sesi) + metadata (hari, slot_per_hari)
 *
 *   POST api.php?action=save&level=N   (body: JSON array sesi)
 *       -> menimpa data/jadwal_level{N}.json dan data/jadwal_level{N}.csv
 *          dengan hasil susunan baru (setelah digeser manual di UI).
 *          Sebuah backup otomatis disimpan di data/backup/ sebelum ditimpa.
 *
 * Field yang WAJIB ada di tiap objek sesi: id_sesi, hari, slot.
 * Field lain (mata_kuliah, dosen, asisten, ruang_lab, peralatan_lab,
 * inventaris_ruang_lab, kelas, warna_graph) hanya diteruskan apa adanya
 * -- tidak divalidasi terhadap conflict graph (validasi bentrok cukup
 * dilakukan di sisi antarmuka/JS agar pengguna tetap bisa menggeser
 * bebas secara manual sesuai kebutuhan nyata).
 */

header("Content-Type: application/json; charset=utf-8");

const DATA_DIR = __DIR__ . "/data";
const BACKUP_DIR = __DIR__ . "/data/backup";
const HARI_DEFAULT = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"];
const SLOT_PER_HARI_DEFAULT = 10;

function fail($msg, $code = 400) {
    http_response_code($code);
    echo json_encode(["ok" => false, "error" => $msg], JSON_UNESCAPED_UNICODE);
    exit;
}

function level_path($level) {
    $level = intval($level);
    if ($level < 1 || $level > 20) fail("Level tidak valid");
    return DATA_DIR . "/jadwal_level{$level}.json";
}

function meta_path($level) {
    // opsional: file data_level{n}.json (dari data_generator.py) untuk
    // mengambil daftar hari & slot_per_hari yang sesungguhnya jika tersedia
    $level = intval($level);
    return DATA_DIR . "/data_level{$level}.json";
}

function get_meta($level) {
    $mp = meta_path($level);
    if (file_exists($mp)) {
        $raw = json_decode(file_get_contents($mp), true);
        if ($raw && isset($raw["hari"]) && isset($raw["slot_per_hari"])) {
            return ["hari" => $raw["hari"], "slot_per_hari" => $raw["slot_per_hari"]];
        }
    }
    return ["hari" => HARI_DEFAULT, "slot_per_hari" => SLOT_PER_HARI_DEFAULT];
}

$action = $_GET["action"] ?? "";

switch ($action) {

    case "levels": {
        $levels = [];
        foreach (glob(DATA_DIR . "/jadwal_level*.json") as $f) {
            if (preg_match('/jadwal_level(\d+)\.json$/', $f, $m)) {
                $levels[] = intval($m[1]);
            }
        }
        sort($levels);
        echo json_encode(["ok" => true, "levels" => $levels], JSON_UNESCAPED_UNICODE);
        break;
    }

    case "load": {
        $level = $_GET["level"] ?? null;
        if (!$level) fail("Parameter 'level' wajib diisi");
        $path = level_path($level);
        if (!file_exists($path)) fail("Data jadwal level {$level} tidak ditemukan", 404);
        $jadwal = json_decode(file_get_contents($path), true);
        if ($jadwal === null) fail("Gagal membaca JSON jadwal (format rusak)");
        $meta = get_meta($level);
        echo json_encode([
            "ok" => true,
            "level" => intval($level),
            "hari" => $meta["hari"],
            "slot_per_hari" => $meta["slot_per_hari"],
            "jadwal" => $jadwal,
        ], JSON_UNESCAPED_UNICODE);
        break;
    }

    case "save": {
        if ($_SERVER["REQUEST_METHOD"] !== "POST") fail("Method harus POST", 405);
        $level = $_GET["level"] ?? null;
        if (!$level) fail("Parameter 'level' wajib diisi");
        $path = level_path($level);

        $body = file_get_contents("php://input");
        $jadwal = json_decode($body, true);
        if (!is_array($jadwal)) fail("Body request harus berupa array JSON sesi");

        foreach ($jadwal as $i => $s) {
            if (!isset($s["id_sesi"]) || !isset($s["hari"]) || !isset($s["slot"])) {
                fail("Sesi pada indeks {$i} tidak memiliki id_sesi/hari/slot");
            }
        }

        // backup otomatis sebelum menimpa
        if (!is_dir(BACKUP_DIR)) mkdir(BACKUP_DIR, 0775, true);
        if (file_exists($path)) {
            $stamp = date("Ymd_His");
            copy($path, BACKUP_DIR . "/jadwal_level{$level}_{$stamp}.json");
        }

        // tulis JSON (rapi, unicode asli, tidak di-escape)
        file_put_contents(
            $path,
            json_encode($jadwal, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
        );

        // tulis CSV pendamping (list/dict diserialisasi sebagai JSON string per sel)
        $csv_path = preg_replace('/\.json$/', '.csv', $path);
        $fh = fopen($csv_path, "w");
        if (count($jadwal) > 0) {
            $headers = array_keys($jadwal[0]);
            fputcsv($fh, $headers);
            foreach ($jadwal as $row) {
                $line = [];
                foreach ($headers as $h) {
                    $v = $row[$h] ?? "";
                    $line[] = is_array($v) ? json_encode($v, JSON_UNESCAPED_UNICODE) : $v;
                }
                fputcsv($fh, $line);
            }
        }
        fclose($fh);

        echo json_encode([
            "ok" => true,
            "message" => "Jadwal level {$level} berhasil disimpan.",
            "jumlah_sesi" => count($jadwal),
            "disimpan_ke" => basename($path) . " & " . basename($csv_path),
        ], JSON_UNESCAPED_UNICODE);
        break;
    }

    default:
        fail("Action tidak dikenal. Gunakan: levels | load | save");
}
