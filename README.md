# 📄 Dokumen Validator - Format Laporan

Aplikasi berbasis **Streamlit** untuk memvalidasi format dokumen laporan (PDF dan DOCX) sesuai dengan standar penulisan akademik.

## 🔍 Fitur

- **Font** – Memastikan semua teks menggunakan Times New Roman
- **Ukuran Font** – Memeriksa apakah ukuran font dominan 12 pt
- **Margin** – Mengukur margin atas, bawah, kiri, kanan (target 3 cm)
- **Jumlah Kata** – Menghitung total kata (di luar daftar pustaka)
- **Perataan** – Mendeteksi apakah teks rata kanan-kiri (justify)
- **Spasi Baris** – Memeriksa apakah spasi sesuai 1.5 (≈18 pt)

## 🚀 Demo Langsung

Akses aplikasi di: [https://dokumen-validator.streamlit.app](https://dokumen-validator.streamlit.app)

## 🛠️ Teknologi

- [Streamlit](https://streamlit.io) – Framework UI
- [pdfplumber](https://github.com/jsvine/pdfplumber) – Ekstraksi dan analisis PDF
- [python-docx](https://github.com/python-openxml/python-docx) – Ekstraksi DOCX
- [PyPDF2](https://pypi.org/project/PyPDF2/) – Metadata PDF

## 📁 Struktur Proyek

```
.
├── app.py                # Aplikasi utama Streamlit
├── requirements.txt      # Dependensi Python
├── README.md             # Dokumentasi
└── utils/
    ├── __init__.py
    ├── pdf_parser.py     # Parser PDF (margin, spacing, justify)
    ├── docx_parser.py    # Parser DOCX (font, ukuran, margin)
    └── validator.py      # Validasi akhir dan laporan
```

## 🖥️ Cara Menjalankan Lokal

1. Clone repository:
   ```bash
   git clone https://github.com/USERNAME/dokumen-validator.git
   cd dokumen-validator
   ```

2. Buat virtual environment (opsional):
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/Mac
   venv\Scripts\activate         # Windows
   ```

3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

4. Jalankan aplikasi:
   ```bash
   streamlit run app.py
   ```

5. Buka browser di `http://localhost:8501`

## 📝 Cara Penggunaan

1. Upload file **PDF** atau **DOCX** melalui tombol di dashboard.
2. Aplikasi akan menganalisis dan menampilkan:
   - Ringkasan dokumen (halaman, kata, ukuran kertas)
   - Hasil validasi per kriteria (✅/❌)
   - Detail per halaman (margin, spacing, justify, font)
3. Gunakan hasil untuk memperbaiki format dokumen sebelum pengumpulan.

## 📊 Contoh Output

- **Jumlah kata**: 2.571 (sesuai range 2000-3000) ✅
- **Margin**: 3.0 cm (konsisten) ✅
- **Font**: Times New Roman (semua halaman) ✅
- **Spasi**: 18.2 pt (≈1.5) ✅
- **Justify**: 100% baris justify ✅

## 📌 Catatan

- Untuk hasil paling akurat, gunakan file **PDF** yang dihasilkan dari **Microsoft Word** dengan format yang sudah benar.
- Margin dihitung dari bounding box teks (bukan dari cropbox), cocok untuk dokumen Word → PDF.
- Spasi dihitung menggunakan median gap antar baris (robust terhadap outlier seperti tabel/gambar).

## 🤝 Kontribusi

Pull request dan issue selalu diterima. Silakan buka issue jika menemukan bug atau ingin menambahkan fitur.
