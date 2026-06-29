import streamlit as st
import pandas as pd
from utils.pdf_parser import (
    extract_text_from_pdf,
    analyze_pdf_format,
    pt_to_cm
)

st.set_page_config(page_title="Validator Format Dokumen", page_icon="📄", layout="wide")

st.title("📄 Validator Format Dokumen Laporan")
st.markdown("""
**Upload file PDF** untuk memeriksa kesesuaian format:
- **Font**: Times New Roman (semua teks)
- **Ukuran**: 12 pt
- **Margin**: 3 cm (atas, bawah, kiri, kanan)
- **Jumlah kata**: 2000–3000 (di luar daftar pustaka)
- **Rata**: kanan-kiri (justify)
- **Spasi**: 1.5 (≈ 18 pt untuk font 12)
""")

with st.sidebar:
    st.header("⚙️ Pengaturan")
    min_words = st.number_input("Minimal kata", value=2000, step=100)
    max_words = st.number_input("Maksimal kata", value=3000, step=100)
    st.markdown("---")
    st.caption("Margin dihitung dari bounding box teks (filter header/footer)")
    st.caption("Spacing dihitung dari median gap antar baris (filter outlier)")

uploaded_file = st.file_uploader("📂 Upload dokumen (PDF)", type=['pdf'])

if uploaded_file:
    file_bytes = uploaded_file.read()
    text = extract_text_from_pdf(file_bytes)
    result = analyze_pdf_format(file_bytes, min_words, max_words)
    
    if 'error' in result:
        st.error(f"Error: {result['error']}")
        st.stop()
    
    # === RINGKASAN ===
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.subheader("📊 Informasi Dokumen")
        col1a, col1b = st.columns(2)
        col1a.metric("📄 Halaman", result['page_count'])
        col1b.metric("📝 Kata Total", result['total_words'])
        col1a.metric("📝 Kata (tanpa daftar pustaka)", result['main_words'])
        col1b.metric("📏 Ukuran Kertas", "A4 ✅" if result['paper_ok'] else "❌")
        if result.get('bibliography_detected', False):
            st.success("📖 Daftar pustaka terdeteksi")
        else:
            st.info("ℹ️ Daftar pustaka tidak terdeteksi")
    
    with col2:
        st.subheader("✅ Hasil Validasi")
        cols = st.columns(4)
        cols[0].metric("📝 Kata", f"{result['main_words']}", "✅" if result['words_ok'] else "❌")
        cols[1].metric("📄 Kertas", "A4" if result['paper_ok'] else "❌", "✅" if result['paper_ok'] else "❌")
        cols[2].metric("📏 Margin", "3 cm" if result['margin_ok'] else "❌", "✅" if result['margin_ok'] else "❌")
        cols[3].metric("🔤 Font", "Times" if result['font_ok'] else "❌", "✅" if result['font_ok'] else "❌")
        cols2 = st.columns(3)
        cols2[0].metric("📏 Ukuran Font", f"{result['avg_font_size']:.1f} pt" if result['avg_font_size'] else "❌", 
                       "✅" if result['font_size_ok'] else "❌")
        cols2[1].metric("📐 Spasi", "1.5" if result['spacing_ok'] else "❌", "✅" if result['spacing_ok'] else "❌")
        cols2[2].metric("📄 Rata", "Justify" if result['justify_ok'] else "❌", "✅" if result['justify_ok'] else "❌")
        
        if result['all_ok']:
            st.success("🎉 **Semua format sudah sesuai!**")
        else:
            st.warning("⚠️ **Ada format yang belum sesuai.**")
            issues = []
            if not result['words_ok']:
                issues.append(f"Jumlah kata {result['main_words']} (harus {min_words}-{max_words})")
            if not result['paper_ok']:
                issues.append("Ukuran kertas bukan A4")
            if not result['margin_ok']:
                issues.append("Margin tidak 3 cm (lihat detail)")
            if not result['font_ok']:
                non = ', '.join(list(result['non_times_fonts'].keys())[:3])
                issues.append(f"Font non-Times: {non}")
            if not result['font_size_ok']:
                issues.append(f"Rata-rata font {result['avg_font_size']:.1f} pt (harus ~12 pt)")
            if not result['spacing_ok']:
                issues.append("Spasi tidak 1.5 (lihat detail)")
            if not result['justify_ok']:
                issues.append("Teks tidak justify (lihat detail)")
            for issue in issues:
                st.write(f"- {issue}")
    
    # === TABEL DETAIL PER HALAMAN ===
    with st.expander("📋 Detail Per Halaman", expanded=False):
        rows = []
        for p in result['page_data']:
            margin = next((m for m in result['margin_details'] if m['page'] == p['page']), None)
            spacing = next((s for s in result['spacing_details'] if s['page'] == p['page']), None)
            justify = next((j for j in result['justify_details'] if j['page'] == p['page']), None)
            
            mg = margin['margins_cm'] if margin else {}
            sp = spacing['spacing_pt'] if spacing else 0
            
            rows.append({
                'Halaman': p['page'],
                'Kata': p['word_count'],
                'Font Size (pt)': f"{p['avg_font_size']:.1f}",
                'Margin Atas (cm)': f"{mg.get('top', 0):.2f}",
                'Margin Bawah (cm)': f"{mg.get('bottom', 0):.2f}",
                'Margin Kiri (cm)': f"{mg.get('left', 0):.2f}",
                'Margin Kanan (cm)': f"{mg.get('right', 0):.2f}",
                'Spasi (pt)': f"{sp:.1f}",
                'Spasi (cm)': f"{pt_to_cm(sp):.2f}",
                'Justify %': f"{justify['percentage']:.1f}%" if justify else "-",
                'Status': "✅" if result['all_ok'] else "⚠️"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400)
    
    # === FONT DETAIL ===
    with st.expander("🔤 Detail Font per Halaman", expanded=False):
        for p in result['page_data']:
            fonts = p['fonts']
            non_times = {f: c for f, c in fonts.items() if not ('Times' in f or 'TimesNewRoman' in f)}
            status = "✅ Semua Times New Roman" if not non_times else f"⚠️ Font non-Times: {', '.join([f'{f} ({c})' for f, c in non_times.items()])}"
            sizes = ', '.join([f"{s:.1f} pt" for s in sorted(p['unique_font_sizes'])]) if p['unique_font_sizes'] else "-"
            st.write(f"**Halaman {p['page']}**: {status}  |  Ukuran: {sizes}")
    
    # === MARGIN DETAIL ===
    with st.expander("📏 Detail Margin (target 3 cm)", expanded=False):
        st.markdown("""
        **Margin dihitung dari jarak teks terluar ke tepi halaman.**
        - Jika ada header/footer (nomor halaman), akan difilter agar tidak mempengaruhi margin.
        - Toleransi: ±0.2 cm dari 3 cm.
        """)
        
        margin_rows = []
        for m in result['margin_details']:
            mg = m['margins_cm']
            margin_rows.append({
                'Halaman': m['page'],
                'Atas (cm)': f"{mg['top']:.2f}",
                'Bawah (cm)': f"{mg['bottom']:.2f}",
                'Kiri (cm)': f"{mg['left']:.2f}",
                'Kanan (cm)': f"{mg['right']:.2f}",
                'Status': "✅" if m['ok'] else "❌",
                'Header/Footer': f"{len(m['header_footer_lines'])} baris terdeteksi"
            })
        df_margin = pd.DataFrame(margin_rows)
        st.dataframe(df_margin, use_container_width=True, height=250)
        
        if not result['margin_ok']:
            st.warning("Beberapa halaman memiliki margin yang tidak sesuai target 3 cm.")
    
    # === SPASI DETAIL ===
    with st.expander("📐 Detail Spasi Baris (target 1.5 / ~18 pt)", expanded=False):
        st.markdown("""
        **Spasi dihitung dari median gap antar baris teks normal.**
        - Baris dengan < 3 karakter diabaikan (bukan teks normal).
        - Outlier (gap > 2x median) diabaikan untuk menghindari tabel/heading.
        - Target: 18 pt ≈ 1.5 × 12 pt.
        """)
        
        for s in result['spacing_details']:
            status = "✅" if s['is_1_5'] else "⚠️"
            st.write(f"{status} **Halaman {s['page']}**: rata-rata {s['spacing_pt']:.1f} pt ({s['spacing_cm']:.2f} cm)")
            
            # Tampilkan detail baris yang tidak 1.5 (maks 5)
            bad_lines = [d for d in s['details'] if not d['is_1_5']]
            if bad_lines and len(bad_lines) <= 5:
                st.write("Baris dengan spacing tidak 1.5:")
                for d in bad_lines:
                    st.write(f"  - Baris {d['line_from']} → {d['line_to']}: {d['gap']:.1f} pt")
            elif bad_lines:
                st.write(f"Terdaftar {len(bad_lines)} baris dengan spacing tidak 1.5 (tidak ditampilkan semua)")
            
            if s.get('outliers'):
                st.write(f"Outlier (diabaikan): {len(s['outliers'])} gap")
            st.markdown("---")
    
    # === JUSTIFY DETAIL ===
    with st.expander("📄 Detail Perataan (harus justify)", expanded=False):
        st.markdown("""
        **Deteksi justify:**
        - Setiap baris dianggap justify jika lebar teks > 80% dari lebar efektif.
        - Halaman dianggap justify jika > 40% baris justify.
        """)
        
        for j in result['justify_details']:
            status = "✅" if j['justify'] else "❌"
            st.write(f"{status} Halaman {j['page']}: {j['justify_lines']}/{j['total_lines']} baris justify ({j['percentage']}%)")
    
    # === PREVIEW ===
    st.subheader("📖 Preview Teks (500 karakter pertama)")
    st.text_area("", text[:500], height=150, disabled=True)

else:
    st.info("👆 Upload file PDF untuk memulai validasi.")
    st.markdown("""
    ### 📝 Kriteria yang Diperiksa
    | Kriteria | Spesifikasi |
    |----------|-------------|
    | **Font** | Times New Roman (semua teks) |
    | **Ukuran Font** | 12 pt |
    | **Margin** | Atas 3, Bawah 3, Kiri 3, Kanan 3 cm |
    | **Jumlah Kata** | 2000 - 3000 kata **(di luar daftar pustaka)** |
    | **Rata** | Rata kanan-kiri (Justify) |
    | **Spasi** | 1.5 (≈ 18 pt) |
    """)

st.caption("🔍 Validator Format Dokumen - Dibuat dengan Streamlit")