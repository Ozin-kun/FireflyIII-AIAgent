# Implementation Tasks & Execution Guide
## Firefly III AI Agent (Level 2)

Dokumen ini adalah panduan kerja (*checklist & task tracking*) untuk pengembang atau AI Agent pada **Antigravity IDE** dalam membangun, memverifikasi, dan menguji sistem AI Agent Level 2 Firefly III.

---

## 📋 Status Komponen Proyek

| Modul | File | Status | Keterangan |
|---|---|:---:|---|
| **Environment & Config** | `config.py`, `.env.example`, `requirements.txt` | [x] Selesai | Pengaturan dependensi, path SQLite & ChromaDB. |
| **REST API Client** | `api/firefly_client.py` | [x] Selesai | Client HTTP resmi Firefly III v1 dengan error handling. |
| **LangChain Tools** | `tools/finance_tools.py` | [x] Selesai | 18 Tools `@tool` (Accounts, Transactions, Budgets/Limits, Piggy Banks, Bills, Categories, Reports). |
| **Dynamic RAG** | `rag/engine.py` | [x] Selesai | ChromaDB vector store dengan incremental delta indexing. |
| **Agentic Memory** | `memory/manager.py` | [x] Selesai | 4-tier memory: SQLite facts, episodes, & MemorySaver. |
| **Agent Harness** | `agent/harness.py` | [x] Selesai | `AgentHarnessCallback` (lifecycle, hooks, circuit breaker). |
| **Loop Engineering** | `agent/loops.py` | [x] Selesai | LangGraph StateGraph (Planning, ReAct, Reflection). |
| **Interactive CLI** | `main.py` | [x] Selesai | Terminal Rich dengan visualisasi Plan & perintah lengkap. |
| **Local Emulator** | `mock_firefly.py` | [x] Selesai | Mock server FastAPI untuk pengujian cepat port 8080. |
| **Dokumentasi** | `PRD.md`, `ARCHITECTURE.md`, `TASKS.md` | [x] Selesai | Spesifikasi produk, arsitektur, dan panduan lengkap. |

---

## 🛠️ Langkah-Langkah Verifikasi di Antigravity IDE

Ketika AI Agent di Antigravity IDE membaca proyek ini, berikut adalah urutan pengujian yang harus dijalankan:

### Tahap 1: Verifikasi Dependensi
Pastikan semua dependensi terpasang di virtual environment:
```powershell
pip install -r requirements.txt
```

### Tahap 2: Menyiapkan File `.env`
Salin template `.env.example` ke `.env`:
```powershell
copy .env.example .env
```
Pastikan variabel berikut terisi:
```env
# Gunakan http://localhost:8085 jika menjalankan Firefly III via Docker Compose
# Gunakan http://localhost:8080 jika menggunakan mock_firefly.py
FIREFLY_BASE_URL=http://localhost:8085
FIREFLY_API_TOKEN=your_personal_access_token_here
GEMINI_API_KEY=AIzaSy... (API Key Google Gemini Anda)
LLM_MODEL=gemini-2.0-flash
```

### Tahap 3: Menjalankan Backend Firefly III
Pilih salah satu metode:
* **Metode Cepat (Tanpa Docker)**:
  ```powershell
  python mock_firefly.py
  ```
  *(Server aktif di `http://localhost:8080` menyediakan data dummy akun BCA, dompet, transaksi, dan budget).*
* **Metode Resmi (Docker Desktop)**:
  ```powershell
  docker compose up -d
  ```

### Tahap 4: Menjalankan AI Agent
Buka terminal baru di direktori proyek:
```powershell
python main.py
```

---

## 🧪 Skenario Pengujian Kriteria Level 2

Untuk membuktikan bahwa sistem telah memenuhi syarat **AI Agent Level 2**, lakukan pengujian dengan skenario berikut di CLI:

### Test 1: ReAct Loop & Tool Execution (Dasar)
* **Prompt Pengguna**:
  > *"Berapa saldo yang ada di rekening utama BCA saya sekarang?"*
* **Ekspektasi Output**:
  - Harness memicu hook `🔧 Tool Action: list_accounts`.
  - Observasi menampilkan data rekening BCA.
  - Agent menjawab dalam bahasa alami dengan nominal saldo yang akurat.

### Test 2: Dynamic RAG (Pencarian Semantik Riwayat)
* **Prompt Pengguna**:
  > *"Kapan terakhir kali saya beli kopi dan berapa harganya?"*
* **Ekspektasi Output**:
  - Harness memanggil tool `semantic_transaction_search` (ChromaDB).
  - RAG menemukan transaksi riwayat kopi sebelumnya.
  - Agent menyebutkan tanggal dan nominal pembelian kopi dari konteks RAG.

### Test 3: Incremental Delta Indexing (RAG Auto-Sync)
* **Prompt Pengguna**:
  > *"Catat pengeluaran baru: beli kopi susu di cafe seharga Rp 28.000 bayar pakai dompet tunai."*
* **Ekspektasi Output**:
  - Agent memanggil tool `create_transaction`.
  - Transaksi berhasil tercatat via API.
  - Log agent otomatis memicu delta sync ke ChromaDB untuk meng-embed transaksi baru tersebut.

### Test 4: Planning Loop (Dekomposisi Multi-Langkah)
* **Prompt Pengguna**:
  > *"Tolong cek sisa limit budget jajan bulanan saya, lalu bandingkan dengan total pengeluaran jajan bulan ini, dan berikan saran penghematan."*
* **Ekspektasi Output**:
  - *Planning Node* mendeteksi instruksi kompleks (`is_complex: true`).
  - Agent menyusun rencana terurut (Step 1: cek budget, Step 2: cek pengeluaran, Step 3: sintesis saran).
  - Agent mengeksekusi tool secara berurutan dan memberikan laporan analisis terpadu.

### Test 5: Agentic Memory (Pembelajaran Preferensi Antar-Sesi)
* **Prompt Pengguna**:
  > *"Mulai sekarang tolong ingat ya, batas maksimal jajan makan siang saya per hari adalah Rp 35.000."*
* **Ekspektasi Output**:
  - *Reflection Node* mengevaluasi percakapan dan mendeteksi preferensi pengguna baru.
  - Fakta disimpan secara persisten ke database SQLite `data/memory.db`.
  - Periksa dengan mengetik perintah CLI:
    ```
    /memory
    ```
  - Fakta `max_lunch_budget` atau preferensi terkait muncul di tabel *Long-Term Rules & Preferences*.
