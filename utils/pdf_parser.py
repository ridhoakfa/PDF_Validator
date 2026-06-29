import io
import pdfplumber
from PyPDF2 import PdfReader
from collections import Counter, defaultdict
import statistics
import re

# ========== UTILITY ==========
def pt_to_cm(pt):
    return pt / 28.346

def cm_to_pt(cm):
    return cm * 28.346

# ========== TEXT EXTRACTION ==========
def extract_text_from_pdf(file_bytes):
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except Exception as e:
        return f"Error: {e}"

# ========== BIBLIOGRAPHY DETECTION ==========
def detect_bibliography(text):
    keywords = ["DAFTAR PUSTAKA", "REFERENCES", "BIBLIOGRAPHY", "REFERENSI"]
    lines = text.split('\n')
    total = len(lines)
    if total == 0:
        return None
    start = int(total * 0.8)
    for i in range(start, total):
        line = lines[i].strip().upper()
        for kw in keywords:
            if kw in line:
                return i
    return None

def extract_text_before_bibliography(text):
    idx = detect_bibliography(text)
    if idx is not None:
        lines = text.split('\n')
        return '\n'.join(lines[:idx])
    return text

# ========== MARGIN DETECTION ==========
def detect_header_footer_lines(page):
    """
    Deteksi baris yang kemungkinan adalah header/footer (nomor halaman)
    """
    chars = page.chars
    if not chars:
        return []
    
    # Kelompokkan per baris
    groups = {}
    for c in chars:
        y = c['y0']
        found = False
        for key in list(groups.keys()):
            if abs(y - key) < 5:
                groups[key].append(c)
                found = True
                break
        if not found:
            groups[y] = [c]
    
    header_footer_lines = []
    page_height = page.height
    
    for y, group in groups.items():
        if len(group) < 2:
            continue
        # Cek apakah posisi baris di 10% teratas atau 10% terbawah
        if y < page_height * 0.1 or y > page_height * 0.9:
            # Cek apakah isinya angka atau teks pendek (nomor halaman)
            text = ''.join([c.get('text', '') for c in group]).strip()
            if len(text) < 10 or text.isdigit():
                header_footer_lines.append(y)
    
    return header_footer_lines

def get_page_margins_detailed(page):
    """
    Mendapatkan margin dari bounding box teks dengan filter header/footer
    """
    chars = page.chars
    if not chars:
        return {'left': 0, 'right': 0, 'top': 0, 'bottom': 0, 'details': []}
    
    # Deteksi header/footer
    header_footer_y = detect_header_footer_lines(page)
    
    # Filter karakter
    chars_filtered = []
    for c in chars:
        is_header_footer = False
        for y in header_footer_y:
            if abs(c['y0'] - y) < 5:
                is_header_footer = True
                break
        if not is_header_footer:
            chars_filtered.append(c)
    
    if not chars_filtered:
        chars_filtered = chars
    
    # Bounding box
    xs = [c['x0'] for c in chars_filtered]
    x1s = [c['x1'] for c in chars_filtered]
    ys = [c['y0'] for c in chars_filtered]
    y1s = [c['y1'] for c in chars_filtered]
    
    margin_left = min(xs) if xs else 0
    margin_right = page.width - max(x1s) if x1s else 0
    margin_top = min(ys) if ys else 0
    margin_bottom = page.height - max(y1s) if y1s else 0
    
    # Detail per sisi
    details = {
        'left': {'value': margin_left, 'min': min(xs) if xs else 0, 'max': max(xs) if xs else 0},
        'right': {'value': margin_right, 'min': page.width - max(x1s) if x1s else 0},
        'top': {'value': margin_top, 'min': min(ys) if ys else 0},
        'bottom': {'value': margin_bottom, 'min': page.height - max(y1s) if y1s else 0}
    }
    
    return {
        'left': margin_left,
        'right': margin_right,
        'top': margin_top,
        'bottom': margin_bottom,
        'details': details,
        'header_footer_lines': header_footer_y,
        'chars_filtered_count': len(chars_filtered),
        'chars_total_count': len(chars)
    }

# ========== SPACING DETECTION ==========
def get_line_groups(page):
    """
    Kelompokkan karakter per baris (toleransi 5 pt)
    """
    chars = page.chars
    if not chars:
        return {}
    
    groups = {}
    for c in chars:
        y = c['y0']
        found = False
        for key in list(groups.keys()):
            if abs(y - key) < 5:
                groups[key].append(c)
                found = True
                break
        if not found:
            groups[y] = [c]
    
    return groups

def detect_line_spacing_detailed(page, avg_font_size=12):
    """
    Deteksi spacing per baris dengan detail
    """
    groups = get_line_groups(page)
    if len(groups) < 2:
        return {'spacing': avg_font_size * 1.5, 'is_1_5': True, 'details': []}
    
    # Filter baris dengan sedikit karakter (bukan teks normal)
    filtered_groups = {}
    for y, group in groups.items():
        if len(group) >= 3:  # minimal 3 karakter
            filtered_groups[y] = group
    
    if len(filtered_groups) < 2:
        filtered_groups = groups
    
    # Urutkan berdasarkan posisi Y
    sorted_ys = sorted(filtered_groups.keys())
    
    # Hitung gap antar baris
    gaps = []
    gap_details = []
    for i in range(len(sorted_ys) - 1):
        gap = sorted_ys[i+1] - sorted_ys[i]
        if 0 < gap < 100:  # batas normal
            gaps.append(gap)
            gap_details.append({
                'line_from': i + 1,
                'line_to': i + 2,
                'gap': gap,
                'is_1_5': abs(gap - 18) <= 2
            })
    
    if not gaps:
        return {'spacing': avg_font_size * 1.5, 'is_1_5': True, 'details': []}
    
    # Median gap (robust terhadap outlier)
    median_gap = statistics.median(gaps)
    
    # Deteksi apakah ada gap yang sangat besar (mungkin karena gambar/table)
    # Jika ada gap > 2x median, tandai sebagai outlier
    outliers = []
    for d in gap_details:
        if d['gap'] > median_gap * 2 and median_gap > 0:
            outliers.append(d)
    
    # Filter outlier
    filtered_gap_details = [d for d in gap_details if d not in outliers]
    filtered_gaps = [d['gap'] for d in filtered_gap_details]
    
    if not filtered_gaps:
        filtered_gaps = gaps
        filtered_gap_details = gap_details
    
    final_median = statistics.median(filtered_gaps) if filtered_gaps else median_gap
    is_1_5 = abs(final_median - 18) <= 2 if final_median > 0 else False
    
    return {
        'spacing': final_median,
        'is_1_5': is_1_5,
        'details': gap_details,
        'outliers': outliers,
        'total_lines': len(filtered_groups),
        'filtered_lines': len(filtered_groups)
    }

# ========== JUSTIFY DETECTION ==========
def detect_justify_detailed(page):
    """
    Deteksi justify dengan detail per baris
    """
    groups = get_line_groups(page)
    if not groups:
        return {'justify': False, 'percentage': 0, 'total_lines': 0, 'justify_lines': 0, 'details': []}
    
    total_lines = len(groups)
    justify_lines = 0
    details = []
    
    page_width = page.width
    
    for y, group in groups.items():
        if len(group) < 3:
            continue
        
        x_min = min(c['x0'] for c in group)
        x_max = max(c['x1'] for c in group)
        width = x_max - x_min
        
        # Lebar efektif = lebar halaman - margin kiri - margin kanan
        left_margin = min(c['x0'] for c in group)
        right_margin = page_width - max(c['x1'] for c in group)
        effective_width = page_width - left_margin - right_margin
        
        # justify jika width > 80% dari effective_width
        justify = (width > 0.80 * effective_width) if effective_width > 0 else False
        
        details.append({
            'y': y,
            'width': width,
            'effective_width': effective_width,
            'justify': justify,
            'percentage': (width / effective_width * 100) if effective_width > 0 else 0
        })
        
        if justify:
            justify_lines += 1
    
    percentage = (justify_lines / total_lines * 100) if total_lines > 0 else 0
    justify = percentage >= 40  # 40% baris justify dianggap justify
    
    return {
        'justify': justify,
        'percentage': round(percentage, 1),
        'total_lines': total_lines,
        'justify_lines': justify_lines,
        'details': details
    }

# ========== MAIN ANALYZER ==========
def get_pdf_detailed_info(file_bytes):
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = len(pdf.pages)
            page_data = []
            total_words = 0
            all_fonts = Counter()
            all_sizes = []
            
            for page_num, page in enumerate(pdf.pages, start=1):
                width = page.width
                height = page.height
                page_text = page.extract_text() or ""
                word_count = len(page_text.split())
                total_words += word_count
                
                # Margin detail
                margin_info = get_page_margins_detailed(page)
                
                # Font
                fonts_on_page = defaultdict(int)
                font_sizes_on_page = []
                for char in page.chars:
                    font = char.get('fontname', 'unknown')
                    fonts_on_page[font] += 1
                    size = char.get('size', 0)
                    if size and size > 1:
                        font_sizes_on_page.append(size)
                        all_sizes.append(size)
                
                avg_font_size = statistics.mean(font_sizes_on_page) if font_sizes_on_page else 0
                unique_font_sizes = sorted(set(font_sizes_on_page)) if font_sizes_on_page else []
                
                # Spacing detail
                spacing_info = detect_line_spacing_detailed(page, avg_font_size)
                
                # Justify detail
                justify_info = detect_justify_detailed(page)
                
                page_data.append({
                    'page': page_num,
                    'width': width,
                    'height': height,
                    'word_count': word_count,
                    'fonts': dict(fonts_on_page),
                    'font_sizes': font_sizes_on_page,
                    'unique_font_sizes': unique_font_sizes,
                    'avg_font_size': avg_font_size,
                    'margin_info': margin_info,
                    'spacing_info': spacing_info,
                    'justify_info': justify_info,
                })
                
                all_fonts.update(fonts_on_page)
            
            # Metadata
            reader = PdfReader(io.BytesIO(file_bytes))
            meta = reader.metadata
            
            return {
                'page_count': pages,
                'page_data': page_data,
                'total_words': total_words,
                'all_fonts': dict(all_fonts),
                'all_sizes': all_sizes,
                'metadata': {
                    'title': meta.get('/Title', 'Tidak tersedia') if meta else 'Tidak tersedia',
                    'author': meta.get('/Author', 'Tidak tersedia') if meta else 'Tidak tersedia',
                    'producer': meta.get('/Producer', 'Tidak tersedia') if meta else 'Tidak tersedia'
                }
            }
    except Exception as e:
        return {'error': str(e)}

# ========== FORMAT VALIDATION ==========
def analyze_pdf_format(file_bytes, min_words=2000, max_words=3000):
    info = get_pdf_detailed_info(file_bytes)
    if 'error' in info:
        return {'error': info['error']}
    
    text = extract_text_from_pdf(file_bytes)
    main_text = extract_text_before_bibliography(text)
    main_word_count = len(main_text.split())
    
    # ===== UKURAN KERTAS =====
    a4_w, a4_h = 595.28, 841.89
    paper_details = []
    paper_ok = True
    for p in info['page_data']:
        w, h = p['width'], p['height']
        ok = (abs(w - a4_w) <= 10 and abs(h - a4_h) <= 10)
        paper_details.append({
            'page': p['page'],
            'width_cm': pt_to_cm(w),
            'height_cm': pt_to_cm(h),
            'ok': ok
        })
        if not ok:
            paper_ok = False
    
    # ===== MARGIN =====
    margin_target_cm = 3.0
    margin_target_pt = cm_to_pt(margin_target_cm)
    margin_tolerance_pt = 5  # toleransi 5 pt ≈ 0.18 cm
    
    margin_details = []
    margin_ok = True
    
    for p in info['page_data']:
        m = p['margin_info']
        margins_cm = {
            'top': pt_to_cm(m['top']),
            'bottom': pt_to_cm(m['bottom']),
            'left': pt_to_cm(m['left']),
            'right': pt_to_cm(m['right'])
        }
        
        # Cek apakah semua margin mendekati target
        ok = all(abs(v - margin_target_cm) <= 0.2 for v in margins_cm.values())
        
        margin_details.append({
            'page': p['page'],
            'margins_cm': margins_cm,
            'margins_pt': {
                'top': m['top'],
                'bottom': m['bottom'],
                'left': m['left'],
                'right': m['right']
            },
            'ok': ok,
            'header_footer_lines': m['header_footer_lines']
        })
        if not ok:
            margin_ok = False
    
    # ===== FONT =====
    all_fonts = info['all_fonts']
    non_times = {f: c for f, c in all_fonts.items() if not ('Times' in f or 'TimesNewRoman' in f)}
    font_ok = len(non_times) == 0
    
    # ===== UKURAN FONT =====
    all_sizes = info.get('all_sizes', [])
    avg_font_size = statistics.mean(all_sizes) if all_sizes else 0
    font_size_ok = 11.0 <= avg_font_size <= 13.0 if avg_font_size > 0 else False
    
    # ===== SPASI =====
    spacing_details = []
    spacing_ok = True
    
    for p in info['page_data']:
        s = p['spacing_info']
        spacing_details.append({
            'page': p['page'],
            'spacing_pt': s['spacing'],
            'spacing_cm': pt_to_cm(s['spacing']) if s['spacing'] > 0 else 0,
            'is_1_5': s['is_1_5'],
            'details': s['details'],
            'outliers': s.get('outliers', [])
        })
        if not s['is_1_5']:
            spacing_ok = False
    
    # ===== JUSTIFY =====
    justify_details = []
    justify_ok = True
    
    for p in info['page_data']:
        j = p['justify_info']
        justify_details.append({
            'page': p['page'],
            'justify': j['justify'],
            'percentage': j['percentage'],
            'total_lines': j['total_lines'],
            'justify_lines': j['justify_lines']
        })
        if not j['justify']:
            justify_ok = False
    
    # ===== JUMLAH KATA =====
    words_ok = min_words <= main_word_count <= max_words
    
    all_ok = all([words_ok, paper_ok, margin_ok, font_ok, font_size_ok, spacing_ok, justify_ok])
    
    return {
        'page_count': info['page_count'],
        'total_words': info['total_words'],
        'main_words': main_word_count,
        'words_ok': words_ok,
        'paper_ok': paper_ok,
        'paper_details': paper_details,
        'margin_ok': margin_ok,
        'margin_details': margin_details,
        'font_ok': font_ok,
        'non_times_fonts': non_times,
        'font_size_ok': font_size_ok,
        'avg_font_size': avg_font_size,
        'spacing_ok': spacing_ok,
        'spacing_details': spacing_details,
        'justify_ok': justify_ok,
        'justify_details': justify_details,
        'page_data': info['page_data'],
        'metadata': info['metadata'],
        'bibliography_detected': detect_bibliography(text) is not None,
        'all_ok': all_ok
    }
