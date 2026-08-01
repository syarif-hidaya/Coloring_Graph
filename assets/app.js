/**
 * app.js
 * ======
 * Logika Editor Jadwal Praktikum:
 * - Memuat jadwal (per level) dari api.php
 * - Merender grid Hari x Slot, tiap sesi jadi kartu draggable
 * - Drag & drop kartu antar slot (di sisi klien / memori dulu)
 * - Deteksi konflik sumber daya secara real-time saat sesi dipindah
 *   (dosen/asisten/ruang_lab/peralatan_lab yang sama di slot yang sama
 *   akan menandai slot tsb dengan highlight merah) -- ini HANYA
 *   peringatan visual, pengguna tetap bebas menyimpan susunan apapun.
 * - Tombol "Simpan Perubahan" mengirim seluruh array sesi (dengan
 *   hari/slot terbaru) ke api.php?action=save untuk ditulis balik ke
 *   file jadwal_level{N}.json (+ .csv), dengan backup otomatis di
 *   server.
 */

const API = "api.php";

let state = {
    level: null,
    hari: [],
    slotPerHari: 10,
    sesi: [],       // array objek sesi (sumber kebenaran saat ini)
    dirty: false,   // ada perubahan yang belum disimpan?
};

const el = {
    levelSelect: document.getElementById("levelSelect"),
    btnReload: document.getElementById("btnReload"),
    btnSave: document.getElementById("btnSave"),
    statusMsg: document.getElementById("statusMsg"),
    loadingMsg: document.getElementById("loadingMsg"),
    grid: document.getElementById("scheduleGrid"),
    headerRow: document.getElementById("gridHeaderRow"),
    gridBody: document.getElementById("gridBody"),
    detailOverlay: document.getElementById("detailOverlay"),
    detailTitle: document.getElementById("detailTitle"),
    detailBody: document.getElementById("detailBody"),
    detailClose: document.getElementById("detailClose"),
};

function setStatus(msg, kind) {
    el.statusMsg.textContent = msg;
    el.statusMsg.className = "status-msg" + (kind ? " " + kind : "");
}

function warnBeforeUnload(e) {
    if (state.dirty) {
        e.preventDefault();
        e.returnValue = "";
    }
}
window.addEventListener("beforeunload", warnBeforeUnload);

// ---------------------------------------------------------------------
// Load daftar level & isi <select>
// ---------------------------------------------------------------------
async function initLevels() {
    const res = await fetch(`${API}?action=levels`);
    const data = await res.json();
    if (!data.ok) { setStatus("Gagal memuat daftar level", "error"); return; }
    el.levelSelect.innerHTML = "";
    data.levels.forEach(lv => {
        const opt = document.createElement("option");
        opt.value = lv;
        opt.textContent = `Level ${lv}`;
        el.levelSelect.appendChild(opt);
    });
    if (data.levels.length > 0) {
        await loadLevel(data.levels[0]);
    }
}

// ---------------------------------------------------------------------
// Load jadwal untuk 1 level dari server
// ---------------------------------------------------------------------
async function loadLevel(level) {
    el.loadingMsg.style.display = "block";
    el.grid.style.display = "none";
    setStatus("");
    try {
        const res = await fetch(`${API}?action=load&level=${level}`);
        const data = await res.json();
        if (!data.ok) { setStatus(data.error || "Gagal memuat data", "error"); return; }
        state.level = data.level;
        state.hari = data.hari;
        state.slotPerHari = data.slot_per_hari;
        state.sesi = data.jadwal;
        state.dirty = false;
        renderGrid();
        setStatus(`Level ${level} dimuat (${state.sesi.length} sesi).`);
    } catch (err) {
        setStatus("Kesalahan jaringan saat memuat data", "error");
    } finally {
        el.loadingMsg.style.display = "none";
        el.grid.style.display = "table";
    }
}

// ---------------------------------------------------------------------
// Render grid Hari x Slot
// ---------------------------------------------------------------------
function renderGrid() {
    // header hari
    el.headerRow.innerHTML = '<th class="corner">Slot</th>';
    state.hari.forEach(h => {
        const th = document.createElement("th");
        th.textContent = h;
        el.headerRow.appendChild(th);
    });

    // kelompokkan sesi per (hari, slot)
    const bucket = {};
    state.sesi.forEach(s => {
        const key = `${s.hari}|${s.slot}`;
        if (!bucket[key]) bucket[key] = [];
        bucket[key].push(s);
    });

    el.gridBody.innerHTML = "";
    for (let slot = 1; slot <= state.slotPerHari; slot++) {
        const tr = document.createElement("tr");
        const tdLabel = document.createElement("td");
        tdLabel.className = "slot-label";
        tdLabel.textContent = `Slot ${slot}`;
        tr.appendChild(tdLabel);

        state.hari.forEach(h => {
            const td = document.createElement("td");
            td.className = "cell";
            td.dataset.hari = h;
            td.dataset.slot = slot;
            attachCellDropHandlers(td);

            const key = `${h}|${slot}`;
            (bucket[key] || []).forEach(s => td.appendChild(buildSessionCard(s)));

            tr.appendChild(td);
        });
        el.gridBody.appendChild(tr);
    }

    refreshConflictHighlights();
}

// ---------------------------------------------------------------------
// Kartu sesi (draggable)
// ---------------------------------------------------------------------
function buildSessionCard(sesi) {
    const card = document.createElement("div");
    card.className = "session-card";
    card.draggable = true;
    card.dataset.id = sesi.id_sesi;

    const course = document.createElement("span");
    course.className = "course";
    course.textContent = sesi.mata_kuliah || sesi.id_sesi;
    card.appendChild(course);

    const sub = document.createElement("span");
    sub.className = "sub";
    sub.textContent = `${sesi.dosen || ""} • ${sesi.ruang_lab || ""}`;
    card.appendChild(sub);

    card.addEventListener("dragstart", (e) => {
        card.classList.add("dragging");
        e.dataTransfer.setData("text/plain", sesi.id_sesi);
        e.dataTransfer.effectAllowed = "move";
    });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    card.addEventListener("click", () => showDetail(sesi));

    return card;
}

// ---------------------------------------------------------------------
// Drag & drop handlers pada tiap sel
// ---------------------------------------------------------------------
function attachCellDropHandlers(td) {
    td.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        td.classList.add("drag-over");
    });
    td.addEventListener("dragleave", () => td.classList.remove("drag-over"));
    td.addEventListener("drop", (e) => {
        e.preventDefault();
        td.classList.remove("drag-over");
        const idSesi = e.dataTransfer.getData("text/plain");
        moveSession(idSesi, td.dataset.hari, parseInt(td.dataset.slot, 10));
    });
}

function moveSession(idSesi, hariBaru, slotBaru) {
    const sesi = state.sesi.find(s => s.id_sesi === idSesi);
    if (!sesi) return;
    if (sesi.hari === hariBaru && sesi.slot === slotBaru) return;

    sesi.hari = hariBaru;
    sesi.slot = slotBaru;
    state.dirty = true;
    setStatus("Ada perubahan belum disimpan — klik 'Simpan Perubahan'.", "");
    renderGrid();
}

// ---------------------------------------------------------------------
// Deteksi konflik sumber daya (visual only)
// ---------------------------------------------------------------------
function konflik(a, b) {
    if (a.dosen && b.dosen && a.dosen === b.dosen) return true;
    if (a.ruang_lab && b.ruang_lab && a.ruang_lab === b.ruang_lab) return true;
    const asistenA = new Set(a.asisten || []);
    if ((b.asisten || []).some(x => asistenA.has(x))) return true;
    const alatA = new Set(a.peralatan_lab || []);
    if ((b.peralatan_lab || []).some(x => alatA.has(x))) return true;
    return false;
}

function refreshConflictHighlights() {
    document.querySelectorAll("#gridBody td.cell").forEach(td => {
        const cards = Array.from(td.querySelectorAll(".session-card"));
        let hasConflict = false;
        if (cards.length > 1) {
            const ids = cards.map(c => c.dataset.id);
            const sesiList = ids.map(id => state.sesi.find(s => s.id_sesi === id));
            outer:
            for (let i = 0; i < sesiList.length; i++) {
                for (let j = i + 1; j < sesiList.length; j++) {
                    if (konflik(sesiList[i], sesiList[j])) { hasConflict = true; break outer; }
                }
            }
        }
        td.classList.toggle("has-conflict", hasConflict);
    });
}

// ---------------------------------------------------------------------
// Panel detail sesi
// ---------------------------------------------------------------------
function showDetail(sesi) {
    el.detailTitle.textContent = `${sesi.mata_kuliah || sesi.id_sesi} (${sesi.kelas || "-"})`;
    let html = "";
    html += detailRow("ID Sesi", sesi.id_sesi);
    html += detailRow("Hari / Slot", `${sesi.hari} — Slot ${sesi.slot}`);
    html += detailRow("Dosen", sesi.dosen);
    html += detailRow("Asisten", (sesi.asisten || []).join(", "));
    html += detailRow("Ruang Lab", sesi.ruang_lab);
    html += detailRow("Peralatan Lab (portable)", (sesi.peralatan_lab || []).join(", "));

    if (sesi.inventaris_ruang_lab && sesi.inventaris_ruang_lab.length > 0) {
        html += '<div class="detail-row"><span class="label">Inventaris Tetap Ruang (RFID)</span>';
        html += '<table class="asset-table"><thead><tr><th>Nama Alat</th><th>RFID</th><th>Kondisi</th></tr></thead><tbody>';
        sesi.inventaris_ruang_lab.forEach(a => {
            html += `<tr><td>${escapeHtml(a.nama_alat)}</td><td>${escapeHtml(a.rfid)}</td><td>${escapeHtml(a.kondisi)}</td></tr>`;
        });
        html += "</tbody></table></div>";
    }

    el.detailBody.innerHTML = html;
    el.detailOverlay.classList.remove("hidden");
}

function detailRow(label, value) {
    return `<div class="detail-row"><span class="label">${escapeHtml(label)}</span>${escapeHtml(value || "-")}</div>`;
}

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

el.detailClose.addEventListener("click", () => el.detailOverlay.classList.add("hidden"));
el.detailOverlay.addEventListener("click", (e) => {
    if (e.target === el.detailOverlay) el.detailOverlay.classList.add("hidden");
});

// ---------------------------------------------------------------------
// Simpan perubahan ke server
// ---------------------------------------------------------------------
async function saveChanges() {
    setStatus("Menyimpan...", "");
    try {
        const res = await fetch(`${API}?action=save&level=${state.level}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(state.sesi),
        });
        const data = await res.json();
        if (!data.ok) { setStatus(data.error || "Gagal menyimpan", "error"); return; }
        state.dirty = false;
        setStatus(`Tersimpan: ${data.disimpan_ke}`, "ok");
    } catch (err) {
        setStatus("Kesalahan jaringan saat menyimpan", "error");
    }
}

// ---------------------------------------------------------------------
// Event wiring
// ---------------------------------------------------------------------
el.levelSelect.addEventListener("change", () => {
    if (state.dirty && !confirm("Ada perubahan belum tersimpan. Ganti level dan buang perubahan?")) {
        el.levelSelect.value = state.level;
        return;
    }
    loadLevel(el.levelSelect.value);
});

el.btnReload.addEventListener("click", () => {
    if (state.dirty && !confirm("Perubahan belum tersimpan akan hilang. Lanjutkan muat ulang?")) return;
    loadLevel(state.level);
});

el.btnSave.addEventListener("click", saveChanges);

initLevels();
