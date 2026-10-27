# Product Requirements Document (PRD)
## AI Agent Level 2: Firefly III Autonomous Finance Assistant

---

## 1. Executive Summary
Proyek ini bertujuan untuk membangun sistem **AI Agent Level 2** otonom yang terintegrasi secara langsung dengan sistem manajemen keuangan pribadi **Firefly III** melalui REST API. 

Berbeda dengan AI Level 1 (chatbot biasa/RAG statis), AI Agent Level 2 ini memiliki otonomi eksekusi multi-langkah (*multi-step execution*), dilengkapi dengan **Loop Engineering** (Planning, ReAct, dan Reflection), **Agent Harness** (lifecycle tracking, observabilitas, dan circuit breaker), **Agentic Memory** 4-lapis (Working, Short-Term, Long-Term, Episodic), serta **Dynamic RAG** yang mampu mengantisipasi perubahan data keuangan yang berfrekuensi tinggi.

---

## 2. Definisi & Kriteria AI Agent Level 2

Sistem ini dirancang untuk memenuhi standar kompetensi AI Agent Level 2:
1. **Goal-Driven Execution**: Agent menerima tujuan abstrak (misal: *"Evaluasi pengeluaran makan minggu ini, jika berlebih buat budget darurat"*), lalu secara mandiri menentukan urutan tindakan tanpa instruksi langkah per langkah dari pengguna.
2. **Tool Use & API Execution**: Mengubah dan mengambil data sistem eksternal secara deterministik via REST API Firefly III.
3. **Loop Engineering**: Menerapkan siklus kognisi eksplisit:
   - *Planning Loop*: Dekomposisi tugas kompleks menjadi sub-tujuan terurut.
   - *ReAct Loop*: Siklus berulang *Reasoning $\rightarrow$ Tool Calling $\rightarrow$ Observation*.
   - *Reflection Loop*: Evaluasi diri pasca-tugas untuk menarik insight dan menyimpannya ke memori jangka panjang.
4. **Agentic Memory Systems**: Menyimpan dan memanggil kembali konteks lintas sesi (fakta, preferensi, dan evaluasi hasil lampau).
5. **Dynamic RAG**: Sinkronisasi data real-time dengan *delta indexing* untuk mengakomodasi frekuensi mutasi transaksi yang tinggi.
6. **Agent Harness**: Menyediakan *runtime containment*, *circuit-breaker error handling*, serta *pre/post execution hooks* untuk keamanan dan transparansi.

---

## 3. User Personas & Use Cases

### User Persona
* **Nama**: Personal Finance Tracker (Mahasiswa / Profesional Muda)
* **Karakter**: Menggunakan Firefly III untuk mencatat mutasi keuangan, tetapi membutuhkan asisten cerdas yang proaktif menganalisis kebiasaan, memberikan rekomendasi budget, dan mencatat transaksi lewat bahasa alami tanpa harus membuka form dashboard berulang kali.

### Core Use Cases (UC)

| ID | Nama Use Case | Deskripsi Alur |
|---|---|---|
| **UC-1** | **Inquiry Saldo & Mutasi** | Pengguna menanyakan saldo atau daftar mutasi terkini. Agent langsung memanggil endpoint API deterministik secara real-time. |
| **UC-2** | **Pencarian Semantik Riwayat** | Pengguna menanyakan kebiasaan atau transaksi lampau dalam bahasa alami (*"Kapan terakhir beli kopi?"*). Agent memanfaatkan Dynamic RAG (ChromaDB) untuk menemukan konteks yang relevan. |
| **UC-3** | **Pencatatan Transaksi Otonom** | Pengguna memberikan instruksi santai (*"Tadi siang makan nasi padang 25rb bayar pakai dompet"*). Agent menyimpulkan jenis transaksi (*withdrawal*), akun asal, kategori, dan nominal lalu membuat transaksi via API. |
| **UC-4** | **Perencanaan Multi-Langkah (Planning)** | Pengguna memberikan instruksi gabungan (*"Cek budget jajan bulan ini, hitung sisa saldo rekening utama, lalu buat laporan singkat"*). Agent mengaktifkan *Planning Node* dan mengeksekusi sub-task berurutan. |
| **UC-5** | **Pembelajaran Preferensi (Memory)** | Pengguna menetapkan aturan (*"Mulai sekarang kalau beli kopi masukkan ke kategori Jajan ya"*). Agent menyimpan preferensi tersebut ke *Long-Term Memory* SQLite dan menggunakannya di interaksi berikutnya. |

---

## 4. Spesifikasi Fungsional (Functional Requirements)

### FR-1: Dynamic RAG (High-Frequency Data Change)
* **FR-1.1**: Sistem harus menggunakan *Vector Store* (ChromaDB) dengan embedding model `models/text-embedding-004`.
* **FR-1.2**: Sistem harus mendukung **Incremental Delta Indexing**, yaitu hanya meng-embed transaksi baru yang ID-nya belum ada di Vector Store.
* **FR-1.3**: Sistem harus memiliki fungsi `sync_with_firefly()` yang dipicu otomatis setelah operasi mutasi transaksi (`create_transaction` / `update_transaction`).
* **FR-1.4**: Sistem harus menyediakan *Semantic Retriever Tool* yang dapat dipanggil oleh LLM saat menjawab pertanyaan analitis atau historis.

### FR-2: Agentic Memory Systems
* **FR-2.1 (Working Memory)**: Mengelola state scratchpad (`plan`, `current_step`, `scratchpad`) dalam siklus eksekusi LangGraph.
* **FR-2.2 (Short-Term Memory)**: Percakapan aktif harus di-*checkpoint* berbasis `thread_id` menggunakan LangGraph Checkpointer (`MemorySaver`).
* **FR-2.3 (Long-Term Memory)**: Menyimpan fakta dan preferensi pengguna (`key`, `value`, `category`) ke database SQLite persisten (`long_term_facts`) dan menginjeksikannya secara dinamis ke system prompt.
* **FR-2.4 (Episodic Memory)**: Menyimpan rekaman refleksi tugas (`user_goal`, `plan`, `outcome`, `learnings`) ke tabel `reflection_episodes` untuk pembelajaran berkelanjutan.

### FR-3: Agent Harness
* **FR-3.1 (Lifecycle Tracking)**: Memantau dan mencatat transisi status agent: `IDLE` $\rightarrow$ `THINKING` $\rightarrow$ `ACTING` $\rightarrow$ `OBSERVING` $\rightarrow$ `ERROR`.
* **FR-3.2 (Execution Hooks)**: Mengimplementasikan `BaseCallbackHandler` LangChain:
  * `on_tool_start`: Pre-execution hook untuk validasi input dan logging.
  * `on_tool_end`: Post-execution hook untuk formatting hasil observasi.
  * `on_tool_error`: Error tracking hook.
* **FR-3.3 (Circuit Breaker)**: Menghitung akumulasi kegagalan per tool. Jika sebuah tool gagal $\ge 3$ kali, harness memutus loop dan meminta agent mengambil strategi alternatif.

### FR-4: Loop Engineering (LangGraph StateGraph)
* **FR-4.1 (Planning Loop)**: Menganalisis kompleksitas pesan pengguna. Jika tergolong kompleks, LLM menyusun rencana terstruktur (`plan: list[str]`).
* **FR-4.2 (ReAct Loop)**: Siklus otonom antara node penalaran (*Agent Node*) dan node eksekusi (*ToolNode*).
* **FR-4.3 (Reflection Loop)**: Evaluasi diri pasca-eksekusi untuk memvalidasi apakah tujuan tercapai dan mendeteksi preferensi pengguna baru untuk disimpan ke Long-Term Memory.

### FR-5: Firefly III Toolkit
Menyediakan sekurang-kurangnya 8 fungsi alat (*tools*) berbasis `@tool` LangChain:
1. `list_accounts`: Daftar akun finansial & saldo.
2. `get_account_details`: Detail akun spesifik.
3. `list_transactions`: Daftar riwayat transaksi dengan filter tanggal & tipe.
4. `search_transactions`: Pencarian kata kunci transaksi.
5. `create_transaction`: Pencatatan mutasi transaksi baru.
6. `list_categories`: Daftar kategori transaksi.
7. `list_budgets`: Daftar anggaran/budget.
8. `get_spending_report`: Ringkasan pengeluaran & pemasukan berkala.

---

## 5. Spesifikasi Non-Fungsional (Non-Functional Requirements)

* **NFR-1 (Security)**: Kredensial API (`GEMINI_API_KEY`, `FIREFLY_API_TOKEN`) wajib dimuat melalui variabel lingkungan (`.env`) dan tidak boleh di-*hardcode*.
* **NFR-2 (Fault Tolerance)**: Jika Firefly III offline, sistem harus memberikan pesan error yang jelas dan memandu pengguna menjalankan mock server atau memeriksa port.
* **NFR-3 (Usability)**: Terminal CLI menggunakan library `rich` dengan pewarnaan visual dan tabel rapi untuk mempermudah monitoring status agent.
* **NFR-4 (Extensibility)**: Arsitektur berbasis LangGraph memungkinkan penambahan node atau tools baru tanpa merombak logika utama.

---

## 6. Kriteria Penerimaan (Acceptance Criteria)

Sistem dinyatakan lulus evaluasi AI Agent Level 2 apabila:
1. ✅ Agent mampu memutuskan pemanggilan tool secara mandiri tanpa disuruh secara eksplisit nama fungsinya.
2. ✅ Dynamic RAG berhasil mendeteksi dan mengindeks transaksi baru setelah pengguna membuat mutasi.
3. ✅ Preferensi yang disebutkan pada sesi chat disimpan ke SQLite dan diingat pada percakapan berikutnya (dibuktikan lewat perintah `/memory`).
4. ✅ Tugas kompleks (multi-langkah) menghasilkan visualisasi *Plan* dan diselesaikan langkah demi langkah secara otonom.
5. ✅ Log eksekusi menampilkan hook *Tool Action* dan *Tool Observation* secara transparan di terminal.
