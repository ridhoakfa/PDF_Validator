import io
import re
import statistics
from collections import defaultdict
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTPage
from PyPDF2 import PdfReader

# ========== UTILITY ==========
def pt_to_cm(pt):
    return pt / 28.346

def cm_to_pt(cm):
    return cm * 28.346

# ========== TEXT EXTRACTION ==========
def extract_text_from_pdf(file_bytes):
    try:
        text = ""
        with io.BytesIO(file_bytes) as f:
            for page_layout in extract_pages(f):
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        text += element.get_text()
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

# ========== ANALISIS LAYOUT ==========
def get_page_data(file_bytes):
    """Ekstrak data per halaman: ukuran, teks, karakter, font, posisi"""
    pages_data = []
    reader = PdfReader(io.BytesIO(file_bytes))
    num_pages = len(reader.pages)

    with io.BytesIO(file_bytes) as f:
        for i, page_layout in enumerate(extract_pages(f)):
            page_width = page_layout.width
            page_height = page_layout.height
            chars = []
            fonts = defaultdict(int)
            font_sizes = []

            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    for text_line in element:
                        for char in text_line:
                            if isinstance(char, LTChar):
                                fontname = char.fontname
                                size = char.size
                                x0, y0, x1, y1 = char.x0, char.y0, char.x1, char.y1
                                chars.append({
                                    'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                                    'text': char.get_text(),
                                    'font': fontname,
                                    'size': size
                                })
                                fonts[fontname] += 1
                                font_sizes.append(size)

            pages_data.append({
                'page': i+1,
                'width': page_width,
                'height': page_height,
                'chars': chars,
                'fonts': dict(fonts),
                'font_sizes': font_sizes,
                'num_chars': len(chars)
            })
    return pages_data, num_pages

def get_combined_margin(chars, page_width, page_height):
    if not chars:
        return {'left': 0, 'right': 0, 'top': 0, 'bottom': 0}
    xs = [c['x0'] for c in chars]
    x1s = [c['x1'] for c in chars]
    ys = [c['y0'] for c in chars]
    y1s = [c['y1'] for c in chars]
    margin_left = min(xs)
    margin_right = page_width - max(x1s)
    margin_top = min(ys)
    margin_bottom = page_height - max(y1s)
    return {
        'left': margin_left if margin_left > 0 else 0,
        'right': margin_right if margin_right > 0 else 0,
        'top': margin_top if margin_top > 0 else 0,
        'bottom': margin_bottom if margin_bottom > 0 else 0
    }

def group_chars_by_line(chars, tolerance=5):
    lines = []
    if not chars:
        return lines
    sorted_chars = sorted(chars, key=lambda c: c['y0'])
    current_line = []
    current_y = sorted_chars[0]['y0']
    for c in sorted_chars:
        if abs(c['y0'] - current_y) <= tolerance:
            current_line.append(c)
        else:
            if current_line:
                lines.append(current_line)
            current_line = [c]
            current_y = c['y0']
    if current_line:
        lines.append(current_line)
    return lines

def detect_line_spacing(page_data):
    lines = group_chars_by_line(page_data['chars'])
    if len(lines) < 2:
        return {'spacing': 0, 'is_1_5': False, 'details': []}
    # Ambil y0 per baris
    y_positions = sorted([min(c['y0'] for c in line) for line in lines])
    gaps = []
    for i in range(len(y_positions)-1):
        gap = y_positions[i+1] - y_positions[i]
        if 0 < gap < 100:
            gaps.append(gap)
    if not gaps:
        return {'spacing': 0, 'is_1_5': False, 'details': []}
    median_gap = statistics.median(gaps)
    is_1_5 = abs(median_gap - 18) <= 2
    details = [{'line': i+1, 'gap': g, 'is_1_5': abs(g-18)<=2} for i,g in enumerate(gaps)]
    return {'spacing': median_gap, 'is_1_5': is_1_5, 'details': details}

def detect_justify(page_data):
    lines = group_chars_by_line(page_data['chars'])
    if not lines:
        return {'justify': False, 'percentage': 0, 'total_lines': 0, 'justify_lines': 0}
    page_width = page_data['width']
    total_lines = len(lines)
    justify_lines = 0
    for line in lines:
        if not line:
            continue
        x0 = min(c['x0'] for c in line)
        x1 = max(c['x1'] for c in line)
        text_width = x1 - x0
        # lebar efektif = lebar halaman - margin kiri - margin kanan (dari baris)
        left_margin = min(c['x0'] for c in line)
        right_margin = page_width - max(c['x1'] for c in line)
        effective_width = page_width - left_margin - right_margin
        if effective_width > 0 and text_width > 0.80 * effective_width:
            justify_lines += 1
    percentage = (justify_lines / total_lines * 100) if total_lines > 0 else 0
    justify = percentage >= 40
    return {'justify': justify, 'percentage': round(percentage,1), 'total_lines': total_lines, 'justify_lines': justify_lines}

# ========== FORMAT VALIDATION ==========
def analyze_pdf_format(file_bytes, min_words=2000, max_words=3000):
    pages_data, page_count = get_page_data(file_bytes)
    text = extract_text_from_pdf(file_bytes)
    main_text = extract_text_before_bibliography(text)
    main_word_count = len(main_text.split())
    total_words = len(text.split())

    # === KERTAS ===
    a4_w, a4_h = 595.28, 841.89
    paper_ok = True
    paper_details = []
    for p in pages_data:
        w, h = p['width'], p['height']
        ok = (abs(w - a4_w) <= 10 and abs(h - a4_h) <= 10)
        paper_details.append({'page': p['page'], 'width_cm': pt_to_cm(w), 'height_cm': pt_to_cm(h), 'ok': ok})
        if not ok:
            paper_ok = False

    # === MARGIN ===
    margin_target_pt = cm_to_pt(3.0)
    margin_tolerance = 10
    margin_ok = True
    margin_details = []
    for p in pages_data:
        margins = get_combined_margin(p['chars'], p['width'], p['height'])
        margins_cm = {k: pt_to_cm(v) for k,v in margins.items()}
        ok = all(abs(v - margin_target_pt) <= margin_tolerance for v in margins.values())
        margin_details.append({
            'page': p['page'],
            'margins_cm': margins_cm,
            'margins_pt': margins,
            'ok': ok
        })
        if not ok:
            margin_ok = False

    # === FONT ===
    all_fonts = defaultdict(int)
    for p in pages_data:
        for f, cnt in p['fonts'].items():
            all_fonts[f] += cnt
    non_times = {f: c for f, c in all_fonts.items() if not ('Times' in f or 'TimesNewRoman' in f)}
    font_ok = len(non_times) == 0

    # === UKURAN FONT ===
    all_sizes = [s for p in pages_data for s in p['font_sizes']]
    avg_font_size = statistics.mean(all_sizes) if all_sizes else 0
    font_size_ok = 11.0 <= avg_font_size <= 13.0

    # === SPASI ===
    spacing_details = []
    spacing_ok = True
    for p in pages_data:
        sp = detect_line_spacing(p)
        spacing_details.append({
            'page': p['page'],
            'spacing_pt': sp['spacing'],
            'spacing_cm': pt_to_cm(sp['spacing']) if sp['spacing']>0 else 0,
            'is_1_5': sp['is_1_5'],
            'details': sp['details']
        })
        if not sp['is_1_5']:
            spacing_ok = False

    # === JUSTIFY ===
    justify_details = []
    justify_ok = True
    for p in pages_data:
        j = detect_justify(p)
        justify_details.append({'page': p['page'], 'justify': j['justify'], 'percentage': j['percentage'], 'total_lines': j['total_lines'], 'justify_lines': j['justify_lines']})
        if not j['justify']:
            justify_ok = False

    # === JUMLAH KATA ===
    words_ok = min_words <= main_word_count <= max_words

    all_ok = all([words_ok, paper_ok, margin_ok, font_ok, font_size_ok, spacing_ok, justify_ok])

    return {
        'page_count': page_count,
        'total_words': total_words,
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
        'page_data': pages_data,
        'bibliography_detected': detect_bibliography(text) is not None,
        'all_ok': all_ok
    }
