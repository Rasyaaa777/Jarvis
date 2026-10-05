# ⚡ JARVIS - Desktop AI Assistant with Voice, Tools & Web Dashboard

Asisten AI desktop berbasis Python untuk Windows yang dilengkapi pengenalan suara (*wake-word* "Hey Jarvis"), integrasi aplikasi lokal/PWA/UWP, persistensi jadwal pengingat di database SQLite, dan Interactive Web Dashboard bergaya *Cybernetic Glassmorphism*.

---

## 💻 Persyaratan Sistem & Instalasi di Device Baru

Untuk menjalankan JARVIS di laptop atau komputer lain, Anda **HANYA memerlukan Python**:
- ❌ **TIDAK butuh Node.js / npm** (Dashboard web murni menggunakan Vanilla HTML/JS yang disajikan langsung oleh Python internal).
- ✅ **Sistem Operasi:** Windows 10 atau Windows 11 (64-bit).
- ✅ **Python:** Versi **3.10 - 3.14** (Wajib centang **"Add python.exe to PATH"** saat instalasi).
- ✅ **Hardware:** Mikrofon, Speaker, dan Koneksi Internet aktif.

---

### 📦 Langkah Instalasi di Device Lain:

1. **Clone repository ini atau salin folder proyek:**
   ```powershell
   git clone https://github.com/Rasyaaa777/Jarvis.git
   cd Jarvis
   ```

2. **(Direkomendasikan) Buat & Aktifkan Virtual Environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install semua dependensi Python (Cukup 1 baris):**
   ```powershell
   pip install -r requirements.txt
   ```
   *(Perintah ini akan otomatis mengunduh seluruh 15 library inti beserta paket pendukungnya).*

4. **Konfigurasi API Key (.env):**
   Salin file `.env.example` menjadi `.env`, lalu masukkan API Key Anda:
   ```powershell
   copy .env.example .env
   ```
   Buka file `.env` dan isi kunci:
   ```ini
   GEMINI_API_KEY=AIzaSy...
   OPENAI_API_KEY=sk-...
   ACTIVE_PROVIDER=gemini
   ```

---

## 🚀 Quick Start (Cara Menjalankan)

Setelah dependensi terpasang, pilih salah satu mode berikut:

1. **Web Dashboard Interaktif (Lengkap dengan UI Chat & Kontrol):**
   ```powershell
   python main.py web
   ```
   *(Browser akan terbuka otomatis di `http://127.0.0.1:5050`)*

2. **Mode Suara / Wake-Word ("Hey Jarvis"):**
   ```powershell
   python main.py wake
   ```

3. **Mode Chat Teks Terminal:**
   ```powershell
   python main.py text
   ```

4. **Dashboard Log & Metrik di Terminal (Rich CLI):**
   ```powershell
   python main.py dashboard
   ```

5. **Jalankan di System Tray (Latar Belakang Windows):**
   ```powershell
   python main.py tray
   ```

---

## 🛠️ Fitur Utama
- **Multi-Provider AI Router:** Otomatis switch antara Google Gemini (`gemini-3.1-flash-lite`) dan OpenAI (`gpt-4o-mini`) dengan fitur auto-fallback.
- **Peluncur Aplikasi Cerdas:** Membuka aplikasi desktop standar, Chrome/Edge PWA (Spotify, CapCut), hingga Windows Store UWP Apps via *fuzzy matching*.
- **Pengingat Mandiri & Persisten (SQLite WAL):** Pengingat tersimpan di database lokal dan tetap berdering tepat waktu walau aplikasi sempat ditutup.
- **Pencarian Web Multi-Engine:** Bing Search + Wikipedia bahasa Indonesia secara otomatis saat AI membutuhkan data terkini.
- **Suara Manusia Neural:** Menggunakan Edge TTS suara bahasa Indonesia jernih (`id-ID-ArdiNeural`).
- **Audit Penggunaan & Biaya:** Real-time tracking latensi, token input/output, dan estimasi biaya per request.

---

## 📚 Dokumentasi Terkait
- 📖 [PANDUAN_DAN_CARA_KERJA.md](./PANDUAN_DAN_CARA_KERJA.md) - Dokumentasi komprehensif arsitektur hulu-ke-hilir, diagram alur, dan cara kerja setiap modul.
- 📦 [INSTALLED_PACKAGES.md](./INSTALLED_PACKAGES.md) - Rincian lengkap seluruh library Python dan package sistem yang digunakan.
