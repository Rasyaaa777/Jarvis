# ⚡ JARVIS - Desktop AI Assistant with Voice, Tools & Web Dashboard

Asisten AI desktop berbasis Python untuk Windows yang dilengkapi pengenalan suara (*wake-word* "Hey Jarvis"), integrasi aplikasi lokal/PWA/UWP, persistensi jadwal pengingat di database SQLite, dan Interactive Web Dashboard bergaya *Cybernetic Glassmorphism*.

---

## 🚀 Quick Start (Cara Cepat Menjalankan)

1. **Jalankan Web Dashboard Interaktif:**
   ```powershell
   python main.py web
   ```
   *(Browser akan terbuka otomatis di `http://127.0.0.1:5050`)*

2. **Jalankan Mode Suara ("Hey Jarvis"):**
   ```powershell
   python main.py wake
   ```

3. **Jalankan Mode Chat Teks:**
   ```powershell
   python main.py text
   ```

4. **Buka Dashboard Metrik & Log di Terminal:**
   ```powershell
   python main.py dashboard
   ```

5. **Jalankan di System Tray (Latar Belakang Windows):**
   ```powershell
   python main.py tray
   ```

---

## 📖 Dokumentasi Lengkap & Tutorial Pindah Device

Penjelasan mendalam tentang **cara kerja arsitektur program**, diagram alur, fungsi tiap folder, serta **tutorial langkah-demi-langkah memasang JARVIS di komputer/laptop lain** dapat dibaca di:

👉 **[PANDUAN_DAN_CARA_KERJA.md]**
---

## 🛠️ Fitur Utama
- **Multi-Provider AI Router:** Otomatis switch antara Google Gemini (`gemini-3.1-flash-lite`) dan OpenAI (`gpt-4o-mini`).
- **Peluncur Aplikasi Cerdas:** Mendukung aplikasi desktop standar, Chrome/Edge PWA (Spotify, CapCut), dan Windows Store UWP Apps.
- **Pengingat Persisten (SQLite):** Pengingat tersimpan di database lokal mode WAL dan tetap berdering saat jatuh tempo walau aplikasi sempat ditutup.
- **Pencarian Web Multi-Engine:** Bing Search + Wikipedia bahasa Indonesia dengan auto-fallback.
- **Suara Manusia Neural:** Menggunakan Edge TTS suara bahasa Indonesia jernih (`id-ID-ArdiNeural`).
- **Audit Penggunaan & Biaya:** Pencatatan latensi, token input/output, dan perkiraan biaya setiap permintaan.
