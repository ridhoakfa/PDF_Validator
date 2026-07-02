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
    page_title="Validator Format Dokumen",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.markdown("### 📋 Panduan Singkat")
    st.markdown("""
    Aplikasi ini memeriksa kesesuaian format dokumen laporan Anda.

    **Kriteria yang diperiksa:**
    - **Font**: Times New Roman
    - **Ukuran font**: 12 pt
    - **Margin**: 3 cm (atas, bawah, kiri, kanan)
    - **Jumlah kata**: 2000–3000 **(di luar daftar pustaka, lampiran, dan HEADER)**
    - **Perataan**: Justify (rata kanan-kiri)
    - **Spasi**: 1.5 (≈ 18 pt) – gap 6–30 pt dianggap OK

    **Cara baca visualisasi:**
    - 🟥 **Garis merah** = batas margin 3 cm
    - 🟦 **Garis biru** = posisi ideal baris berikutnya (18 pt)
    - 🟩 **Label hijau** = gap OK (6–30 pt)
    - 🟧 **Label oranye** = gap >30 pt (antar paragraf, bukan error)
    - 🟥 **Label merah** = gap <6 pt (terlalu rapat)
    - 🟨 **Area kuning** = area header (diabaikan dari validasi)
    """)

    st.markdown("---")
    st.markdown("""
    **👨‍💻 Dibuat oleh:**  
    **Ridho Akbar Fadhilah**  
    NIM: 24050123130116  
    Statistika – Universitas Diponegoro
    """)

st.title("📄 Validator Format Dokumen Laporan")
st.markdown("Upload file PDF untuk memeriksa kesesuaian format sesuai standar penulisan akademik.")

uploaded_file = st.file_uploader(
    "📂 Upload dokumen (PDF)",
    type=['pdf'],
    help="Upload file PDF laporan Anda untuk divalidasi"
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    text = extract_text_from_pdf(file_bytes)
    result = analyze_pdf_format(file_bytes, min_words=2000, max_words=3000)

    if 'error' in result:
        st.error(f"Error: {result['error']}")
        st.stop()

    # ========== RINGKASAN DOKUMEN ==========
    st.subheader("📊 Ringkasan Dokumen")

    col_info1, col_info2, col_info3, col_info4, col_info5 = st.columns(5)
    with col_info1:
        st.metric("📄 Halaman", result['page_count'])
    with col_info2:
        st.metric("📝 Kata (tanpa dafpus, lampiran, header)", result['main_words'])
    with col_info3:
        st.metric("📏 Ukuran Kertas", "A4 ✅" if result['paper_ok'] else "❌")
    with col_info4:
        if result.get('bibliography_detected', False):
            st.metric("📖 Daftar Pustaka", "Terdeteksi ✅")
        else:
            st.metric("📖 Daftar Pustaka", "Tidak terdeteksi ⚠️")
    with col_info5:
        if result.get('attachment_detected', False):
            st.metric("📎 Lampiran", "Terdeteksi ✅")
        else:
            st.metric("📎 Lampiran", "Tidak terdeteksi ⚠️")

    # ========== DETAIL PEMBAGIAN DOKUMEN ==========
    with st.expander("📊 Detail Pembagian Dokumen (Kata & Halaman)", expanded=False):
        part_details = result.get('part_details', {})
        if part_details:
            data = []
            for name, detail in part_details.items():
                label = {
                    'main': '📄 Bagian Utama',
                    'bibliography': '📖 Daftar Pustaka',
                    'attachment': '📎 Lampiran'
                }.get(name, name.capitalize())
                word_count = detail['word_count']
                page_range = detail['page_range'] if detail['page_range'] else "(kosong)"
                data.append({
                    'Bagian': label,
                    'Jumlah Kata': word_count,
                    'Halaman': page_range
                })
            df_parts = pd.DataFrame(data)
            st.dataframe(df_parts, use_container_width=True, hide_index=True)

            total_main = part_details.get('main', {}).get('word_count', 0)
            total_bib = part_details.get('bibliography', {}).get('word_count', 0)
            total_att = part_details.get('attachment', {}).get('word_count', 0)
            st.caption(f"**Total kata utama:** {total_main} | **Daftar pustaka:** {total_bib} | **Lampiran:** {total_att}")
        else:
            st.info("Tidak ada deteksi batas dokumen (semua teks dianggap bagian utama).")

    # ========== STATUS VALIDASI ==========
    st.subheader("✅ Status Validasi")

    status_cols = st.columns(7)
    status_items = [
        ("📝 Kata", "words_ok", "2000-3000"),
        ("📏 Margin", "margin_ok", "3 cm"),
        ("🔤 Font", "font_ok", "Times New Roman"),
        ("📏 Ukuran Font", "font_size_ok", "12 pt"),
        ("📐 Spasi", "spacing_ok", "1.5"),
        ("📄 Rata", "justify_ok", "Justify"),
        ("📄 Kertas", "paper_ok", "A4")
    ]

    for i, (label, key, target) in enumerate(status_items):
        with status_cols[i]:
            ok = result.get(key, False)
            st.markdown(f"**{label}**  \n: {':white_check_mark:' if ok else ':x:'} {target}")

    if not result['all_ok']:
        st.warning("⚠️ Ada format yang belum sesuai. Periksa detail di bawah.")
        issues = []
        if not result['words_ok']:
            issues.append(f"Jumlah kata {result['main_words']} (harus 2000-3000)")
        if not result['paper_ok']:
            issues.append("Ukuran kertas bukan A4")
        if not result['margin_ok']:
            issues.append("Margin tidak sesuai (lihat detail)")
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
    else:
        st.success("🎉 **Semua format sudah sesuai!**")

    # ========== VISUALISASI PER HALAMAN ==========
    st.subheader("🖼️ Visualisasi Per Halaman dengan Garis Panduan")

    page_options = list(range(1, result['page_count'] + 1))
    selected_page = st.selectbox("Pilih halaman untuk dilihat", page_options, index=0)

    img_bytes = render_page_with_guidelines(file_bytes, selected_page, dpi=100)
    if img_bytes:
        st.image(img_bytes, caption=f"Halaman {selected_page} (Area kuning = header diabaikan)", use_container_width=True)
    else:
        st.warning("Gagal merender halaman")

    # ========== ANALISIS DEVIASI HALAMAN TERPILIH ==========
    deviation = analyze_page_deviations(file_bytes, selected_page)
    if deviation and 'error' not in deviation:
        col_dev1, col_dev2, col_dev3, col_dev4 = st.columns(4)

        with col_dev1:
            st.markdown("#### 📏 Margin (3 cm)")
            st.write(f"**Target:** 3.00 cm")
            st.write(f"**Aktual:** Kiri={deviation['actual_margins_cm']['left']:.2f}cm, Kanan={deviation['actual_margins_cm']['right']:.2f}cm, Atas={deviation['actual_margins_cm']['top']:.2f}cm, Bawah={deviation['actual_margins_cm']['bottom']:.2f}cm")
            st.write("**Status:**")
            for side in ['left', 'right', 'top', 'bottom']:
                status = deviation['margin_status'][side]
                emoji = "✅" if "AMAN" in status else "❌"
                st.write(f"- {side.capitalize()}: {emoji} {status}")
            st.write(f"**Sumber margin:** {deviation.get('margin_source', 'unknown')}")

        with col_dev2:
            st.markdown("#### 📐 Spasi (1.5 / 18 pt)")
            if deviation['spacing_deviations']:
                ok_lines = [d for d in deviation['spacing_deviations'] if d['status'] == 'OK']
                extra_lines = [d for d in deviation['spacing_deviations'] if d['status'] == 'ANTAR PARAGRAF']
                bad_lines = [d for d in deviation['spacing_deviations'] if d['status'] == 'TERLALU RAPAT']
                st.write(f"**Total baris:** {len(deviation['spacing_deviations'])}")
                st.write(f"**✅ OK (6–30 pt):** {len(ok_lines)} baris")
                st.write(f"**🟧 Antar paragraf (>30 pt):** {len(extra_lines)} baris")
                st.write(f"**❌ Terlalu rapat (<6 pt):** {len(bad_lines)} baris")
                st.write("**Detail (maks 10):**")
                for d in deviation['spacing_deviations'][:10]:
                    if d['status'] == 'OK':
                        st.write(f"✅ Baris {d['line']}: {d['gap_pt']:.1f} pt (deviasi {d['deviation_pt']:+.1f} pt) – OK")
                    elif d['status'] == 'ANTAR PARAGRAF':
                        st.write(f"🟧 Baris {d['line']}: {d['gap_pt']:.1f} pt – antar paragraf")
                    else:
                        st.write(f"❌ Baris {d['line']}: {d['gap_pt']:.1f} pt (deviasi {d['deviation_pt']:+.1f} pt) – {d['status']}")
                if len(deviation['spacing_deviations']) > 10:
                    st.write(f"... dan {len(deviation['spacing_deviations']) - 10} baris lainnya")
            else:
                st.write("✅ Tidak ada data spacing")

        with col_dev3:
            st.markdown("#### 📄 Perataan (Justify)")
            st.write(f"**Persentase justify:** {deviation['justify_percentage']}%")
            st.write(f"**Status:** {'✅ OK' if deviation['justify_ok'] else '❌ Tidak justify (minimal 40%)'}")

        with col_dev4:
            st.markdown("#### 📌 Header")
            if deviation.get('has_header', False):
                st.write(f"✅ Terdeteksi {deviation['header_count']} baris header")
                st.write("Lihat detail di bagian '📌 Detail Header per Halaman' di bawah.")
            else:
                st.write("✅ Tidak ada header terdeteksi")

    # ========== TABEL DETAIL PER HALAMAN ==========
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
                'Font (pt)': f"{p['avg_font_size']:.1f}",
                'Margin Atas (cm)': f"{mg.get('top', 0):.2f}",
                'Margin Bawah (cm)': f"{mg.get('bottom', 0):.2f}",
                'Margin Kiri (cm)': f"{mg.get('left', 0):.2f}",
                'Margin Kanan (cm)': f"{mg.get('right', 0):.2f}",
                'Spasi (pt)': f"{sp:.1f}",
                'Justify %': f"{justify['percentage']:.1f}%" if justify else "-",
                'Header': "✅" if p.get('has_header', False) else "❌",
                'Margin OK': "✅" if margin['ok'] else "❌"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400)

    # ========== FONT DETAIL ==========
    with st.expander("🔤 Detail Font per Halaman (tanpa header)", expanded=False):
        for p in result['page_data']:
            fonts = p['fonts']
            non_times = {f: c for f, c in fonts.items() if not ('Times' in f or 'TimesNewRoman' in f)}
            status = "✅ Semua Times New Roman" if not non_times else f"⚠️ Font non-Times: {', '.join([f'{f} ({c})' for f, c in non_times.items()])}"
            sizes = ', '.join([f"{s:.1f} pt" for s in sorted(p['unique_font_sizes'])]) if p['unique_font_sizes'] else "-"
            st.write(f"**Halaman {p['page']}**: {status}  |  Ukuran: {sizes}")

    # ========== MARGIN DETAIL ==========
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

    # ========== SPASI DETAIL ==========
    with st.expander("📐 Detail Spasi Baris (target 1.5 / ~18 pt)", expanded=False):
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

    # ========== JUSTIFY DETAIL ==========
    with st.expander("📄 Detail Perataan (Justify) per Halaman", expanded=False):
        avg_justify = sum(j['percentage'] for j in result['justify_details']) / len(result['justify_details']) if result['justify_details'] else 0
        st.write(f"**Rata-rata persentase justify seluruh dokumen:** {avg_justify:.1f}%")
        justify_rows = []
        for j in result['justify_details']:
            justify_rows.append({
                'Halaman': j['page'],
                'Justify': "✅" if j['justify'] else "❌",
                'Persentase': f"{j['percentage']:.1f}%",
                'Baris Justify': j['justify_lines'],
                'Total Baris (valid)': j['total_lines'],
                'Status': "OK" if j['justify'] else "Tidak OK"
            })
        df_justify = pd.DataFrame(justify_rows)
        st.dataframe(df_justify, use_container_width=True, height=200)
        if not result['justify_ok']:
            st.warning("Beberapa halaman memiliki persentase justify di bawah 40%. Periksa tabel.")

    # ========== HEADER DETAIL ==========
    with st.expander("📌 Detail Header per Halaman", expanded=False):
        st.markdown("""
        **Header adalah teks di area 10% atas halaman.**
        - Header **tidak dihitung** dalam jumlah kata, font, ukuran, spacing, maupun justify.
        - Berikut detail header yang terdeteksi per halaman.
        """)
        header_found = False
        for p in result['page_data']:
            if p.get('has_header', False):
                header_found = True
                st.markdown(f"**Halaman {p['page']}** — {len(p['header_details'])} baris header")
                header_rows = []
                for i, h in enumerate(p['header_details'], 1):
                    header_rows.append({
                        'Baris ke-': i,
                        'Teks': h['text'][:60] + ('...' if len(h['text']) > 60 else ''),
                        'Font': h['font'],
                        'Ukuran (pt)': h['size'],
                        'Posisi Y': h['y_pos']
                    })
                if header_rows:
                    df_header = pd.DataFrame(header_rows)
                    st.dataframe(df_header, use_container_width=True, hide_index=True)
                st.markdown("---")
        if not header_found:
            st.info("Tidak ada header yang terdeteksi pada dokumen ini.")

    # ========== FOOTER ==========
    st.markdown("---")
    st.caption("🔍 Validator Format Dokumen – Dibuat oleh Ridho Akbar Fadhilah (24050123130116) | Statistika Universitas Diponegoro")

else:
    st.info("👆 Upload file PDF untuk memulai validasi.")

    st.markdown("""
    ### 📝 Kriteria yang Diperiksa
    | Kriteria | Spesifikasi | Toleransi |
    |----------|-------------|-----------|
    | **Font** | Times New Roman (semua teks) | - |
    | **Ukuran Font** | 12 pt | ±1 pt |
    | **Margin** | Atas 3, Bawah 3, Kiri 3, Kanan 3 cm | ±0.2 cm |
    | **Jumlah Kata** | 2000 - 3000 kata **(di luar daftar pustaka, lampiran, dan HEADER)** | - |
    | **Rata** | Rata kanan-kiri (Justify) | ≥40% baris justify |
    | **Spasi** | 1.5 (≈ 18 pt) | ±12 pt (6–30 pt OK) |
    | **Kertas** | A4 | - |
    """)

    st.markdown("---")
    st.caption("🔍 Validator Format Dokumen – Dibuat oleh Ridho Akbar Fadhilah (24050123130116) | Statistika Universitas Diponegoro")
