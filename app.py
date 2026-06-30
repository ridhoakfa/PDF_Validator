import streamlit as st
import pandas as pd
from utils.pdf_parser import (
    extract_text_from_pdf,
    analyze_pdf_format,
    analyze_page_deviations,
    render_page_with_guidelines,
    pt_to_cm
)

st.set_page_config(
    page_title="Validator Format Dokumen Laporan",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== HEADER =====
st.markdown("""
# 📄 Validator Format Dokumen Laporan
**Upload file PDF** untuk memeriksa kesesuaian format sesuai standar penulisan akademik.
""")

st.markdown("""
| Kriteria | Spesifikasi |
|----------|-------------|
| **Font** | Times New Roman (semua teks) |
| **Ukuran Font** | 12 pt |
| **Margin** | Atas 3, Bawah 3, Kiri 3, Kanan 3 cm |
| **Jumlah Kata** | 2000 – 3000 (di luar daftar pustaka) |
| **Perataan** | Rata kanan-kiri (Justify) |
| **Spasi** | 1.5 (≈ 18 pt) – gap 6–30 pt dianggap OK |
""")

# ===== FILE UPLOADER =====
uploaded_file = st.file_uploader(
    "📂 Upload file PDF",
    type=['pdf'],
    help="Seret atau klik untuk memilih file PDF"
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    text = extract_text_from_pdf(file_bytes)
    result = analyze_pdf_format(file_bytes, min_words=2000, max_words=3000)
    
    if 'error' in result:
        st.error(f"Error: {result['error']}")
        st.stop()
    
    # ===== INFORMASI DOKUMEN =====
    with st.container():
        st.markdown("### 📊 Informasi Dokumen")
        col_info = st.columns(5)
        col_info[0].metric("📄 Halaman", result['page_count'])
        col_info[1].metric("📝 Kata Total", result['total_words'])
        col_info[2].metric("📝 Kata (tanpa daftar pustaka)", result['main_words'])
        col_info[3].metric("📏 Ukuran Kertas", "A4 ✅" if result['paper_ok'] else "❌")
        col_info[4].metric("📖 Daftar Pustaka", "Terdeteksi" if result.get('bibliography_detected', False) else "Tidak terdeteksi")
    
    # ===== HASIL VALIDASI =====
    st.markdown("### ✅ Hasil Validasi")
    col_valid = st.columns(7)
    col_valid[0].metric("📝 Kata", "✅" if result['words_ok'] else "❌")
    col_valid[1].metric("📄 Kertas", "✅" if result['paper_ok'] else "❌")
    col_valid[2].metric("📏 Margin", "✅" if result['margin_ok'] else "❌")
    col_valid[3].metric("🔤 Font", "✅" if result['font_ok'] else "❌")
    col_valid[4].metric("📏 Ukuran Font", "✅" if result['font_size_ok'] else "❌")
    col_valid[5].metric("📐 Spasi", "✅" if result['spacing_ok'] else "❌")
    col_valid[6].metric("📄 Rata", "✅" if result['justify_ok'] else "❌")
    
    if result['all_ok']:
        st.success("🎉 **Semua format sudah sesuai!**")
    else:
        st.warning("⚠️ **Ada format yang belum sesuai.**")
        issues = []
        if not result['words_ok']:
            issues.append(f"Jumlah kata {result['main_words']} (harus 2000-3000)")
        if not result['paper_ok']:
            issues.append("Ukuran kertas bukan A4")
        if not result['margin_ok']:
            issues.append("Margin < 3 cm pada beberapa halaman (lihat detail)")
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
    
    # ===== VISUALISASI PER HALAMAN =====
    st.markdown("### 🖼️ Visualisasi Per Halaman dengan Garis Panduan")
    st.caption("""
    - **Garis Merah** = batas margin 3 cm.
    - **Garis Biru** = posisi ideal baris berikutnya jika spacing 1.5 (18 pt), dihitung dari baris sebelumnya.
    - **Hijau** = gap OK (6–30 pt). **Oranye** = gap >30 pt (antar paragraf). **Merah** = gap <6 pt (terlalu rapat).
    """)
    
    selected_page = st.selectbox(
        "Pilih Halaman",
        options=list(range(1, result['page_count'] + 1)),
        index=0
    )
    
    img_bytes = render_page_with_guidelines(file_bytes, selected_page, dpi=100)
    if img_bytes:
        st.image(img_bytes, caption=f"Halaman {selected_page}", use_container_width=True)
    else:
        st.warning("Gagal merender halaman")
    
    # ===== ANALISIS DEVIASI HALAMAN =====
    deviation = analyze_page_deviations(file_bytes, selected_page)
    if deviation and 'error' not in deviation:
        col_dev = st.columns(3)
        with col_dev[0]:
            st.markdown("#### 📏 Margin")
            st.write(f"**Aktual:** Kiri={deviation['actual_margins_cm']['left']:.2f}cm, Kanan={deviation['actual_margins_cm']['right']:.2f}cm, Atas={deviation['actual_margins_cm']['top']:.2f}cm, Bawah={deviation['actual_margins_cm']['bottom']:.2f}cm")
            for side in ['left', 'right', 'top', 'bottom']:
                status = deviation['margin_status'][side]
                emoji = "✅" if "AMAN" in status else "❌"
                st.write(f"{emoji} {side.capitalize()}: {status}")
            st.caption(f"Sumber margin: {deviation.get('margin_source', 'unknown')}")
        
        with col_dev[1]:
            st.markdown("#### 📐 Spacing")
            if deviation['spacing_deviations']:
                ok_lines = [d for d in deviation['spacing_deviations'] if d['status'] == 'OK']
                extra_lines = [d for d in deviation['spacing_deviations'] if d['status'] == 'ANTAR PARAGRAF']
                bad_lines = [d for d in deviation['spacing_deviations'] if d['status'] == 'TERLALU RAPAT']
                st.write(f"**Total baris:** {len(deviation['spacing_deviations'])}")
                st.write(f"✅ OK (6–30 pt): {len(ok_lines)} baris")
                st.write(f"🟧 Antar paragraf (>30 pt): {len(extra_lines)} baris")
                st.write(f"❌ Terlalu rapat (<6 pt): {len(bad_lines)} baris")
                with st.expander("Lihat detail baris (maks 10)"):
                    for d in deviation['spacing_deviations'][:10]:
                        if d['status'] == 'OK':
                            st.write(f"✅ Baris {d['line']}: {d['gap_pt']:.1f} pt (deviasi {d['deviation_pt']:+.1f} pt)")
                        elif d['status'] == 'ANTAR PARAGRAF':
                            st.write(f"🟧 Baris {d['line']}: {d['gap_pt']:.1f} pt (antar paragraf)")
                        else:
                            st.write(f"❌ Baris {d['line']}: {d['gap_pt']:.1f} pt (terlalu rapat)")
            else:
                st.write("✅ Tidak ada data spacing (halaman kosong atau hanya 1 baris)")
        
        with col_dev[2]:
            st.markdown("#### 📄 Perataan (Justify)")
            st.write(f"**Persentase justify:** {deviation['justify_percentage']}%")
            st.write("✅ OK" if deviation['justify_ok'] else "❌ Tidak justify (minimal 40%)")
    
    # ===== TABEL DETAIL PER HALAMAN =====
    with st.expander("📋 Detail Per Halaman (Tabel)", expanded=False):
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
                'Justify %': f"{justify['percentage']:.1f}%" if justify else "-",
                'Margin OK': "✅" if margin['ok'] else "❌"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400)
    
    # ===== FONT DETAIL =====
    with st.expander("🔤 Detail Font per Halaman", expanded=False):
        for p in result['page_data']:
            fonts = p['fonts']
            non_times = {f: c for f, c in fonts.items() if not ('Times' in f or 'TimesNewRoman' in f)}
            status = "✅ Semua Times New Roman" if not non_times else f"⚠️ Font non-Times: {', '.join([f'{f} ({c})' for f, c in non_times.items()])}"
            sizes = ', '.join([f"{s:.1f} pt" for s in sorted(p['unique_font_sizes'])]) if p['unique_font_sizes'] else "-"
            st.write(f"**Halaman {p['page']}**: {status}  |  Ukuran: {sizes}")
    
    # ===== MARGIN DETAIL =====
    with st.expander("📏 Detail Margin (target 3 cm)", expanded=False):
        margin_rows = []
        for m in result['margin_details']:
            mg = m['margins_cm']
            margin_rows.append({
                'Halaman': m['page'],
                'Kata': m['word_count'],
                'Atas (cm)': f"{mg['top']:.2f}",
                'Bawah (cm)': f"{mg['bottom']:.2f}",
                'Kiri (cm)': f"{mg['left']:.2f}",
                'Kanan (cm)': f"{mg['right']:.2f}",
                'Status': "✅" if m['ok'] else "❌",
                'Sumber': m.get('source', 'unknown')
            })
        df_margin = pd.DataFrame(margin_rows)
        st.dataframe(df_margin, use_container_width=True, height=250)
        if not result['margin_ok']:
            st.warning("Beberapa halaman memiliki margin < 3 cm. Periksa tabel.")
    
    # ===== SPASI DETAIL =====
    with st.expander("📐 Detail Spasi Baris (target 1.5 / ~18 pt)", expanded=False):
        st.caption("Gap >30 pt = antar paragraf (bukan error line spacing), gap <6 pt = terlalu rapat.")
        for s in result['spacing_details']:
            status = "✅" if s['is_1_5'] else "⚠️"
            st.write(f"{status} **Halaman {s['page']}**: median gap {s['spacing_pt']:.1f} pt ({s['spacing_cm']:.2f} cm)")
            bad_lines = [d for d in s['details'] if not d['is_1_5']]
            if bad_lines:
                st.write("Detail gap yang tidak OK:")
                for d in bad_lines:
                    if d['gap'] > 30:
                        st.write(f"  🟧 Baris {d['line_from']} → {d['line_to']}: {d['gap']:.1f} pt – antar paragraf")
                    elif d['gap'] < 6:
                        st.write(f"  ❌ Baris {d['line_from']} → {d['line_to']}: {d['gap']:.1f} pt – terlalu rapat")
                    else:
                        st.write(f"  ⚠️ Baris {d['line_from']} → {d['line_to']}: {d['gap']:.1f} pt – tidak OK")
            else:
                st.write("✅ Semua gap OK.")
            st.markdown("---")
    
    # ===== FOOTER =====
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888; font-size: 14px;">
            Dibuat oleh <strong>Ridho Akbar Fadhilah</strong> (NIM 24050123130116) &bull; 
            Validator Format Dokumen &bull; <a href="https://github.com/ridhoakfa/PDF_Validator" target="_blank">GitHub</a>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    | **Spasi** | 1.5 (≈ 18 pt) – gap 6–30 pt OK |
    """)
