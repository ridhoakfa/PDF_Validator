# 📄 Validator Format Dokumen Laporan

Aplikasi berbasis **Streamlit** untuk memvalidasi format dokumen laporan (PDF) sesuai dengan standar penulisan akademik. Membantu penulis memeriksa kesesuaian font, margin, jumlah kata, perataan, dan spasi secara otomatis.

---

## 🔍 Fitur

| Fitur | Deskripsi |
|-------|-----------|
| **Font** | Memastikan semua teks menggunakan Times New Roman (per halaman) |
| **Ukuran Font** | Memeriksa apakah ukuran font dominan 12 pt |
| **Margin** | Mengukur margin atas, bawah, kiri, kanan (target 3 cm) |
| **Jumlah Kata** | Menghitung total kata di luar daftar pustaka (target 2000–3000) |
| **Perataan** | Mendeteksi apakah teks rata kanan-kiri (justify) per halaman |
| **Spasi Baris** | Memeriksa apakah spasi sesuai 1.5 (≈18 pt) |
| **Ukuran Kertas** | Validasi ukuran kertas A4 |

---

## 🚀 Demo Langsung

**Akses aplikasi:** [https://pdf-validator.streamlit.app/](https://pdf-validator.streamlit.app/)

---

## 🛠️ Teknologi

- [Streamlit](https://streamlit.io) – Framework UI interaktif
- [pdfplumber](https://github.com/jsvine/pdfplumber) – Ekstraksi dan analisis PDF
- [PyPDF2](https://pypi.org/project/PyPDF2/) – Membaca metadata PDF
- [python-docx](https://github.com/python-openxml/python-docx) – Ekstraksi DOCX (opsional)
- [Pandas](https://pandas.pydata.org/) – Manipulasi data untuk tampilan tabel

---

## 📁 Struktur Proyek

```
.
├── app.py                # Aplikasi utama Streamlit
├── requirements.txt      # Dependensi Python
├── runtime.txt           # Menentukan versi Python (3.12)
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
   - **Ringkasan dokumen** (halaman, kata, ukuran kertas)
   - **Hasil validasi** per kriteria (✅/❌) dengan status jelas
   - **Detail per halaman** (margin, spacing, justify, font, ukuran font)
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

## 📌 Catatan Penting

- Untuk hasil paling akurat, gunakan file **PDF** yang dihasilkan dari **Microsoft Word** dengan format yang sudah benar.
- Margin dihitung dari **bounding box teks** (bukan dari cropbox), yang cocok untuk dokumen Word → PDF.
- Spasi dihitung menggunakan **median gap** antar baris, robust terhadap outlier (tabel, heading, gambar).
- **Deteksi margin dan spasi** masih dalam tahap penyempurnaan untuk meningkatkan akurasi.

---

## 📂 Repository

Kode sumber tersedia di: [https://github.com/ridhoakfa/PDF_Validator](https://github.com/ridhoakfa/PDF_Validator)

---

## 🤝 Kontribusi

Pull request dan issue selalu diterima. Silakan buka issue jika menemukan bug atau ingin menambahkan fitur.

---

---

**Dibuat dengan ❤️ oleh Ridho Akbar Fadhilah**
