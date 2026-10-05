# 📦 Daftar Package & Library yang Terpasang di Sistem

Dokumen ini mencatat seluruh paket, pustaka (*library*), serta lingkungan eksekusi (*runtime*) yang terpasang di perangkat Anda dan digunakan oleh proyek **JARVIS**.

> **Terakhir Diperbarui:** 2026-10-05  
> **Sistem Operasi:** Windows (64-bit)  
> **Python Version:** 3.14.7  
> **Node.js Version:** v24.19.0 (NPM: 11.17.0)

---

## 1. 🐍 Python Packages (Proyek JARVIS)

### A. Dependensi Utama (Core Libraries)
Paket-paket utama yang tercantum dalam [`requirements.txt`](file:///d:/%23RASYA/project%20random/JARVIS/requirements.txt) beserta fungsinya:

| Nama Paket | Versi | Fungsi / Peran di JARVIS |
| :--- | :--- | :--- |
| **`google-genai`** | `2.21.0` | SDK resmi Google Gemini AI (Model default: `gemini-2.5-flash` / `gemini-3.1-flash-lite`) |
| **`openai`** | `3.6.0` | SDK OpenAI untuk provider alternatif / failover (`gpt-4o-mini`) |
| **`edge-tts`** | `7.2.8` | Sintesis suara Microsoft Edge Neural TTS (suara natural bahasa Indonesia / Jarvis) |
| **`pyttsx3`** | `2.99` | Text-to-Speech offline cadangan (Windows SAPI5) |
| **`SpeechRecognition`** | `3.17.0` | Pengenal suara ke teks (*Speech-to-Text*) via mikrofon |
| **`sounddevice`** | `0.5.6` | Antarmuka I/O audio berlatensi rendah untuk menangkap suara mikrofon |
| **`numpy`** | `2.5.2` | Pengolahan array numerik & kalkulasi buffer suara dari mikrofon |
| **`rapidfuzz`** | `3.14.6` | Pencocokan string pintar (*fuzzy matching*) untuk mengenali nama aplikasi Windows |
| **`pywin32`** | `312` | Integrasi Win32 API Windows (buka aplikasi, kontrol window, shortcut) |
| **`requests`** | `2.34.2` | HTTP Client untuk fetching data dan web scraping |
| **`beautifulsoup4`** | `4.15.0` | Parser HTML untuk mengekstrak isi teks hasil pencarian Bing & Wikipedia |
| **`rich`** | `15.0.0` | Tampilan visual terminal interaktif berwarna, panel, tabel, dan live dashboard |
| **`pystray`** | `0.19.5` | Ikon System Tray Windows (pojok kanan bawah taskbar) |
| **`pillow`** | `12.3.0` | Pemrosesan citra / gambar untuk ikon System Tray dan visual assets |
| **`python-dotenv`** | `1.2.3` | Membaca konfigurasi API Key dan variabel lingkungan dari file `.env` |

---

### B. Daftar Lengkap Seluruh Paket Python Terpasang (`pip list`)

Berikut adalah seluruh pustaka termasuk dependensi turunan (*transitive dependencies*):

```text
Package                      Version
---------------------------- ---------
aiohappyeyeballs             2.7.1
aiohttp                      3.14.3
aiosignal                    1.4.0
annotated-types              0.8.0
anyio                        4.14.2
attrs                        26.1.0
audioop-lts                  0.2.2
beautifulsoup4               4.15.0
certifi                      2026.7.22
cffi                         2.1.1
charset-normalizer           3.5.1
colorama                     0.4.6
comtypes                     1.4.16
cryptography                 50.0.1
distro                       1.9.0
docopt                       0.6.2
edge-tts                     7.2.8
frozenlist                   1.8.0
google-ai-generativelanguage 0.6.15
google-api-core              2.25.2
google-api-python-client     2.200.0
google-auth                  2.57.0
google-auth-httplib2         0.4.2
google-genai                 2.21.0
google-generativeai          0.8.6
googleapis-common-protos     1.75.0
grpcio                       1.83.1
grpcio-status                1.71.2
h11                          0.16.0
httpcore                     1.0.9
httpcore2                    2.12.0
httplib2                     0.32.0
httpx                        0.28.1
httpx2                       2.12.0
idna                         3.19
jiter                        0.16.0
Js2Py                        0.74
markdown-it-py               4.2.0
mdurl                        0.1.2
multidict                    6.9.0
numpy                        2.5.2
openai                       3.6.0
packaging                    26.3
pillow                       12.3.0
pip                          26.2.1
pipwin                       0.5.2
propcache                    0.5.4
proto-plus                   1.28.2
protobuf                     5.29.6
pyasn1                       0.6.4
pyasn1_modules               0.4.2
pycparser                    3.0
pydantic                     2.13.5
pydantic_core                2.46.5
Pygments                     2.21.0
pyjsparser                   2.7.1
pyparsing                    3.3.2
pypiwin32                    223
PyPrind                      2.11.3
pySmartDL                    1.3.4
pystray                      0.19.5
python-dotenv                1.2.3
pyttsx3                      2.99
pywin32                      312
RapidFuzz                    3.14.6
requests                     2.34.2
rich                         15.0.0
six                          1.17.0
sniffio                      1.3.1
sounddevice                  0.5.6
soupsieve                    2.9.2
SpeechRecognition            3.17.0
standard-aifc                3.13.0
standard-chunk               3.13.0
tabulate                     0.10.0
tenacity                     9.1.4
tqdm                         4.70.0
truststore                   0.10.4
typing_extensions            4.16.0
typing-inspection            0.4.4
tzdata                       2026.3
tzlocal                      5.4.4
uritemplate                  4.2.0
urllib3                      2.7.0
websockets                   16.1.1
yarl                         1.25.1
```

---

## 2. 🌐 Node.js & NPM Packages

### A. Status di Proyek JARVIS
- **Tidak ada dependensi npm lokal (`node_modules`).**
- Web Dashboard ([`dashboard/web/static/index.html`](file:///d:/%23RASYA/project%20random/JARVIS/dashboard/web/static/index.html)) dibangun murni menggunakan **Vanilla HTML, Vanilla CSS, dan Vanilla JavaScript** tanpa bundler eksternal, sehingga tidak memerlukan `npm install`.

### B. Global NPM Packages di Sistem (`npm list -g --depth=0`)

| Package Global | Versi | Keterangan |
| :--- | :--- | :--- |
| **`@opencode/cli`** | `2.0.20` | CLI agent untuk terminal AI / coding assistant |

---

## 3. 💡 Perintah Bantuan untuk Update / Cek Berkala

Jika di kemudian hari Anda ingin memperbarui atau memeriksa daftar paket:

- **Cek daftar paket Python terkini:**
  ```powershell
  python -m pip list
  ```
- **Simpan freeze paket Python ke file:**
  ```powershell
  pip freeze > installed_freeze.txt
  ```
- **Cek paket global Node.js / NPM:**
  ```powershell
  npm list -g --depth=0
  ```
