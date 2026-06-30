# 📄 Validator Format Dokumen Laporan

Aplikasi berbasis **Streamlit** untuk memvalidasi format dokumen laporan (PDF) secara otomatis sesuai standar penulisan akademik. Membantu penulis memeriksa kesesuaian font, margin, jumlah kata, perataan, dan spasi secara detail per halaman.

---

## 🔍 Fitur Utama

| Fitur | Deskripsi | Target |
|-------|-----------|--------|
| **🔤 Font** | Memeriksa apakah semua teks menggunakan Times New Roman | Times New Roman |
| **📏 Ukuran Font** | Rata-rata ukuran font dominan | 12 pt (±1 pt) |
| **📐 Margin** | Mengukur margin atas, bawah, kiri, kanan | 3 cm (±0.2 cm) |
| **📝 Jumlah Kata** | Menghitung kata di luar daftar pustaka | 2000–3000 kata |
| **📄 Perataan** | Mendeteksi persentase baris justify per halaman | ≥40% baris justify |
| **📊 Spasi Baris** | Median gap antar baris | 18 pt (6–30 pt dianggap OK) |
| **📃 Ukuran Kertas** | Validasi ukuran kertas | A4 |

---

## 🖥️ Demo Langsung

**Akses aplikasi:** [https://pdf-validator.streamlit.app/](https://pdf-validator.streamlit.app/)

---

## 🛠️ Teknologi

- [Streamlit](https://streamlit.io) – Framework UI interaktif
- [PyMuPDF (fitz)](https://pypi.org/project/PyMuPDF/) – Ekstraksi dan analisis PDF
- [python-docx](https://github.com/python-openxml/python-docx) – Ekstraksi DOCX (opsional)
- [Pandas](https://pandas.pydata.org/) – Manipulasi data untuk tampilan tabel
- [Pillow](https://python-pillow.org/) – Rendering visualisasi halaman

---

## 📁 Struktur Proyek

```
.
├── app.py                # Aplikasi utama Streamlit
├── requirements.txt      # Dependensi Python
├── runtime.txt           # Versi Python (3.12)
├── README.md             # Dokumentasi
└── utils/
    ├── __init__.py
    ├── pdf_parser.py     # Parser PDF (margin, spacing, justify, font)
    ├── docx_parser.py    # Parser DOCX (font, ukuran, margin)
    └── validator.py      # Validasi akhir dan laporan
```

---

## 🖥️ Cara Menjalankan Lokal

1. **Clone repository**
   ```bash
   git clone https://github.com/ridhoakfa/PDF_Validator.git
   cd PDF_Validator
   ```

2. **Buat virtual environment (disarankan)**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/Mac
   venv\Scripts\activate         # Windows
   ```

3. **Install dependensi**
   ```bash
   pip install -r requirements.txt
   ```

4. **Jalankan aplikasi**
   ```bash
   streamlit run app.py
   ```

5. **Buka browser** di `http://localhost:8501`

---

## 📝 Cara Penggunaan

1. Upload file **PDF** melalui tombol di dashboard.
2. Aplikasi akan menganalisis dan menampilkan:
   - **Ringkasan dokumen** (halaman, kata, ukuran kertas, deteksi daftar pustaka)
   - **Status validasi** per kriteria (✅/❌) dengan target jelas
   - **Visualisasi halaman** dengan garis panduan margin dan spacing
   - **Detail per halaman** dalam tabel (margin, spacing, justify, font, ukuran font)
   - **Rekomendasi perbaikan** jika ada format yang belum sesuai

---

## 📊 Contoh Output

| Kriteria | Status | Nilai |
|----------|--------|-------|
| Jumlah Kata | ✅ | 2.571 (sesuai 2000-3000) |
| Margin | ✅ | 3.0 cm (konsisten) |
| Font | ✅ | Times New Roman (semua halaman) |
| Ukuran Font | ✅ | 12.0 pt |
| Spasi | ✅ | 18.2 pt (≈1.5) |
| Perataan | ✅ | 92% baris justify |
| Ukuran Kertas | ✅ | A4 |

---

## 🧠 Metode Deteksi

### Margin
- Prioritas: **Cropbox PDF** (jika ada)
- Fallback: **Bounding box teks** dari semua baris
- Toleransi: ±0.2 cm

### Spasi Baris
- Menggunakan **median gap** antar baris (robust terhadap outlier)
- Gap >30 pt dianggap **antar paragraf** (bukan error)
- Gap <6 pt dianggap **terlalu rapat** (error)

### Perataan (Justify)
- Baris dianggap justify jika:
  1. Lebar baris ≥80% dari lebar efektif (margin kiri–kanan)
  2. Ujung kanan baris dalam toleransi **5 pt** dari margin kanan
- Baris dengan <3 kata diabaikan (heading, nomor halaman, dll.)
- Minimal **40% baris** justify per halaman

---

## 📌 Catatan Penting

- Untuk hasil paling akurat, gunakan file **PDF** yang dihasilkan dari **Microsoft Word** dengan format yang sudah benar.
- Margin dihitung dari **bounding box teks** (fallback) atau **cropbox** (prioritas), cocok untuk dokumen Word → PDF.
- Spasi dihitung menggunakan **median gap** antar baris, robust terhadap outlier (tabel, heading, gambar).
- **Deteksi daftar pustaka** menggunakan kata kunci: `DAFTAR PUSTAKA`, `REFERENCES`, `BIBLIOGRAPHY`, `REFERENSI`.

---

## 📂 Repository

Kode sumber tersedia di: [https://github.com/ridhoakfa/PDF_Validator](https://github.com/ridhoakfa/PDF_Validator)

---

## 🤝 Kontribusi

Pull request dan issue selalu diterima. Silakan buka issue jika menemukan bug atau ingin menambahkan fitur.

---

## 📜 Lisensi

Proyek ini menggunakan lisensi **MIT** – silakan gunakan dan modifikasi sesuai kebutuhan.

---

## 👨‍💻 Pembuat

**Ridho Akbar Fadhilah**  
NIM: 24050123130116  
Statistika – Universitas Diponegoro  

---

**Dibuat dengan ❤️**
