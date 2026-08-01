<?php
/**
 * index.php
 * =========
 * Halaman utama Editor Jadwal Praktikum.
 * Menampilkan grid Senin-Jumat x slot, memuat data lewat api.php (AJAX),
 * dan mengizinkan sesi digeser (drag & drop) antar slot lalu disimpan
 * kembali ke file jadwal_level{N}.json melalui api.php.
 */
?>
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Editor Jadwal Praktikum</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<header class="topbar">
    <h1>📅 Editor Jadwal Praktikum</h1>
    <div class="topbar-controls">
        <label for="levelSelect">Level:</label>
        <select id="levelSelect"></select>
        <button id="btnReload" class="btn btn-secondary" title="Muat ulang dari file (perubahan belum tersimpan akan hilang)">⟳ Muat Ulang</button>
        <button id="btnSave" class="btn btn-primary">💾 Simpan Perubahan</button>
        <span id="statusMsg" class="status-msg"></span>
    </div>
</header>

<div class="legend">
    <span class="legend-item"><span class="dot dot-ok"></span> Slot aman</span>
    <span class="legend-item"><span class="dot dot-conflict"></span> Slot bentrok sumber daya (dosen/asisten/ruang/alat)</span>
    <span class="legend-item hint">Seret (drag) kartu sesi ke slot lain untuk menggeser jadwal secara manual.</span>
</div>

<div id="gridWrapper" class="grid-wrapper">
    <div id="loadingMsg" class="loading-msg">Memuat data...</div>
    <table id="scheduleGrid" class="schedule-grid" style="display:none;">
        <thead>
            <tr id="gridHeaderRow"><th class="corner">Slot</th></tr>
        </thead>
        <tbody id="gridBody"></tbody>
    </table>
</div>

<!-- Panel detail sesi (muncul saat kartu sesi diklik) -->
<div id="detailOverlay" class="overlay hidden">
    <div class="detail-panel">
        <button id="detailClose" class="detail-close">✕</button>
        <h2 id="detailTitle">Detail Sesi</h2>
        <div id="detailBody"></div>
    </div>
</div>

<script src="assets/app.js"></script>
</body>
</html>
