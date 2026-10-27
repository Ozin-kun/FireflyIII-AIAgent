# 🌟 Firefly III AI Financial Agent

Dokumentasi lengkap proyek, instalasi Docker Firefly III, registrasi akun awal, pengambilan token API, serta panduan menjalankan backend dan frontend tersedia pada:

👉 **[README.md Utama di Root Repository](../README.md)**

---

### Ringkasan Cepat Menjalankan AI Agent:

#### 1. Setup Backend:
```bash
# Masuk ke folder agent
cd firefly-aiagent

# Buat virtual environment & install dependensi
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Siapkan .env
cp .env.example .env
# Edit .env dan masukkan FIREFLY_API_TOKEN serta GEMINI_API_KEY

# Jalankan server API
python server.py
# Server aktif di http://localhost:8000
```

#### 2. Setup Frontend Web:
```bash
cd frontend
npm install
npm run dev
# Web app aktif di http://localhost:5173
```

Untuk panduan lengkap langkah demi langkah beserta tangkapan alur Docker dan pengambilan token, silakan baca **[Root README.md](../README.md)**.
