import io
import fitz
from collections import Counter, defaultdict
import statistics
import re
from PIL import Image, ImageDraw, ImageFont

# ========== UTILITY ==========
def pt_to_cm(pt):
    return pt / 28.346

def cm_to_pt(cm):
    return cm * 28.346

# ========== TEXT EXTRACTION ==========
def extract_text_from_pdf(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"Error: {e}"

# ========== DETEKSI BAGIAN YANG DIKECUALIKAN (DAFTAR PUSTAKA & LAMPIRAN) ==========
def find_excluded_section_start(text):
    """
    Cari indeks baris pertama dari bagian yang harus dikecualikan:
    - Daftar Pustaka / Referensi
    - Lampiran / Appendix
    Mengembalikan indeks baris (0-based) atau None jika tidak ditemukan.
    """
    keywords = [
        # Daftar Pustaka
        "DAFTAR PUSTAKA", "REFERENSI", "REFERENCES", "BIBLIOGRAPHY", "PUSTAKA",
        # Lampiran
        "LAMPIRAN", "APPENDIX", "ATTACHMENT", "LAMP.", "APP."
    ]
    lines = text.split('\n')
    total = len(lines)
    if total == 0:
        return None

    # Cari dari atas ke bawah, ambil indeks paling kecil (yang pertama muncul)
    earliest_idx = None
    for i, line in enumerate(lines):
        line_clean = line.strip().upper()
        if not line_clean:
            continue
        for kw in keywords:
            # Cek apakah keyword ada di baris (case-insensitive)
            if kw in line_clean:
                # Hindari false positive: kata "PUSTAKA" mungkin muncul di tengah kalimat
                # tapi biasanya di header hanya ada kata itu saja atau dengan nomor.
                # Kita anggap aman karena di laporan akademik header tersebut eksplisit.
                if earliest_idx is None or i < earliest_idx:
                    earliest_idx = i
                break  # cukup satu keyword per baris

    return earliest_idx

def extract_text_before_excluded_sections(text):
    """
    Kembalikan teks sebelum bagian yang dikecualikan (Daftar Pustaka atau Lampiran).
    Jika tidak ditemukan, kembalikan seluruh teks.
    """
    idx = find_excluded_section_start(text)
    if idx is not None:
        lines = text.split('\n')
        # Ambil semua baris sebelum idx (tidak termasuk baris header)
        return '\n'.join(lines[:idx])
    return text

# ========== GET LINES WITH POSITIONS ==========
def get_lines_with_positions(page):
    """
    Dapatkan daftar baris teks dengan koordinat (x0, y0, x1, y1) dan teks.
    """
    words = page.get_text("words")
    if not words:
        return []
    
    # Kelompokkan kata menjadi baris (toleransi 3 pt)
    lines = []
    current_line = []
    current_y = None
    for w in words:
        x0, y0, x1, y1, word, block, line, word_idx = w
        if current_y is None or abs(y0 - current_y) < 3:
            current_line.append(w)
            if current_y is None:
                current_y = y0
        else:
            if current_line:
                lines.append(current_line)
            current_line = [w]
            current_y = y0
    if current_line:
        lines.append(current_line)
    
    # Filter header/footer (abaikan baris di 10% atas/bawah dengan teks pendek/angka)
    height = page.rect.height
    filtered_lines = []
    for line_words in lines:
        if not line_words:
            continue
        y0 = min(w[1] for w in line_words)
        y1 = max(w[3] for w in line_words)
        text = ' '.join(w[4] for w in line_words)
        is_top = y0 < height * 0.1
        is_bottom = y1 > height * 0.9
        if not ((is_top or is_bottom) and (len(text) < 10 or text.isdigit())):
            x0 = min(w[0] for w in line_words)
            x1 = max(w[2] for w in line_words)
            filtered_lines.append({
                'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                'text': text,
                'words': line_words,
                'line_num': len(filtered_lines) + 1
            })
    
    # Urutkan berdasarkan y0
    filtered_lines.sort(key=lambda l: l['y0'])
    for i, line in enumerate(filtered_lines):
        line['line_num'] = i + 1
    
    return filtered_lines

# ========== GET MARGIN FROM CROPBOX ==========
def get_page_margin(page):
    """
    Dapatkan margin dari cropbox PDF jika ada, fallback ke bounding box teks.
    """
    try:
        media_box = page.mediabox
        crop_box = page.cropbox
        if crop_box and crop_box != media_box:
            left = crop_box[0] - media_box[0]
            bottom = crop_box[1] - media_box[1]
            right = media_box[2] - crop_box[2]
            top = media_box[3] - crop_box[3]
            if left > 0 or right > 0 or top > 0 or bottom > 0:
                return {
                    'left': max(0, left),
                    'right': max(0, right),
                    'top': max(0, top),
                    'bottom': max(0, bottom),
                    'source': 'cropbox'
                }
    except:
        pass
    
    # Fallback: bounding box teks
    lines = get_lines_with_positions(page)
    if not lines:
        return {'left': 0, 'right': 0, 'top': 0, 'bottom': 0, 'source': 'none'}
    all_x0 = [l['x0'] for l in lines]
    all_x1 = [l['x1'] for l in lines]
    all_y0 = [l['y0'] for l in lines]
    all_y1 = [l['y1'] for l in lines]
    width = page.rect.width
    height = page.rect.height
    return {
        'left': min(all_x0) if all_x0 else 0,
        'right': width - max(all_x1) if all_x1 else 0,
        'top': min(all_y0) if all_y0 else 0,
        'bottom': height - max(all_y1) if all_y1 else 0,
        'source': 'text_bbox'
    }

# ========== MAIN ANALYZER ==========
def get_pdf_detailed_info(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = len(doc)
        page_data = []
        total_words = 0
        all_fonts = Counter()
        all_sizes = []

        for page_num in range(pages):
            page = doc[page_num]
            width = page.rect.width
            height = page.rect.height

            # === GET LINES ===
            lines = get_lines_with_positions(page)
            
            # === MARGIN ===
            margin_info = get_page_margin(page)
            
            # === FONT INFO ===
            fonts_on_page = defaultdict(int)
            font_sizes_on_page = []
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font = span["font"]
                            size = span["size"]
                            fonts_on_page[font] += 1
                            if size > 1:
                                font_sizes_on_page.append(size)
                                all_sizes.append(size)
            avg_font_size = statistics.mean(font_sizes_on_page) if font_sizes_on_page else 0
            unique_font_sizes = sorted(set(font_sizes_on_page)) if font_sizes_on_page else []
            
            word_count = len(page.get_text().split())
            total_words += word_count
            
            # === SPACING (per baris) ===
            all_gaps = []
            gap_details = []
            for i in range(len(lines) - 1):
                gap = lines[i+1]['y0'] - lines[i]['y0']
                if 0 < gap < 200:
                    all_gaps.append(gap)
                    gap_details.append({
                        'line_from': i + 1,
                        'line_to': i + 2,
                        'gap': gap,
                        'deviation': gap - 18,
                    })
            
            median_gap = statistics.median(all_gaps) if all_gaps else 0
            
            for d in gap_details:
                gap = d['gap']
                if gap > 30:
                    d['is_1_5'] = True
                    d['status'] = 'ANTAR PARAGRAF'
                    d['deviation'] = gap - 18
                elif gap < 6:
                    d['is_1_5'] = False
                    d['status'] = 'KURANG'
                    d['deviation'] = gap - 18
                else:
                    if abs(gap - median_gap) <= 6:
                        d['is_1_5'] = True
                        d['status'] = 'OK'
                    else:
                        d['is_1_5'] = False
                        d['status'] = 'MELEWATI'
                    d['deviation'] = gap - 18
            
            is_1_5_overall = 6 <= median_gap <= 30
            spacing_info = {
                'spacing': median_gap,
                'is_1_5': is_1_5_overall,
                'details': gap_details,
                'outliers': [],
                'total_lines': len(lines),
                'filtered_lines': len(all_gaps)
            }
            
            # === JUSTIFY ===
            left_margin = margin_info['left']
            right_margin = margin_info['right']
            effective_width = width - left_margin - right_margin
            tolerance = 5
            
            justify_lines = 0
            total_lines_valid = 0
            for line in lines:
                if len(line['words']) < 3:
                    continue
                total_lines_valid += 1
                line_width = line['x1'] - line['x0']
                if (line_width > 0.80 * effective_width and
                    abs(line['x1'] - (width - right_margin)) <= tolerance):
                    justify_lines += 1
            
            percentage = (justify_lines / total_lines_valid * 100) if total_lines_valid > 0 else 0
            justify_info = {
                'justify': percentage >= 40,
                'percentage': round(percentage, 1),
                'total_lines': total_lines_valid,
                'justify_lines': justify_lines
            }
            
            page_data.append({
                'page': page_num + 1,
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
                'lines': lines
            })
            
            all_fonts.update(fonts_on_page)

        doc.close()

        return {
            'page_count': pages,
            'page_data': page_data,
            'total_words': total_words,
            'all_fonts': dict(all_fonts),
            'all_sizes': all_sizes,
            'metadata': {}
        }
    except Exception as e:
        return {'error': str(e)}

# ========== RENDER PAGE WITH GUIDELINES ==========
def render_page_with_guidelines(file_bytes, page_num, dpi=100):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if page_num < 1 or page_num > len(doc):
            return None
        
        page = doc[page_num - 1]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)
        
        width_pt = page.rect.width
        height_pt = page.rect.height
        scale = dpi / 72
        target_margin_pt = cm_to_pt(3.0)
        margin_px = target_margin_pt * scale
        
        draw.rectangle(
            [margin_px, margin_px, 
             pix.width - margin_px, pix.height - margin_px],
            outline=(255, 0, 0),
            width=2
        )
        draw.text((10, 10), "Margin target 3 cm (merah)", fill=(255, 0, 0))
        
        lines = get_lines_with_positions(page)
        if not lines:
            doc.close()
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            return img_bytes.getvalue()
        
        for i, line in enumerate(lines):
            y0_px = line['y0'] * scale
            draw.ellipse([(10, y0_px-2), (14, y0_px+2)], fill=(0, 255, 0))
            
            if i < len(lines) - 1:
                gap_actual = lines[i+1]['y0'] - line['y0']
                ideal_y_px = (line['y0'] + 18) * scale
                draw.line([(20, ideal_y_px), (pix.width - 20, ideal_y_px)], 
                          fill=(0, 100, 255), width=1)
                
                if gap_actual > 30:
                    status_text = " (extra space)"
                    color = (200, 100, 0)
                elif gap_actual < 6:
                    status_text = " (terlalu rapat)"
                    color = (255, 0, 0)
                else:
                    if 6 <= gap_actual <= 30:
                        status_text = ""
                        color = (0, 150, 0)
                    else:
                        status_text = " (deviasi)"
                        color = (255, 165, 0)
                
                label = f"{gap_actual:.1f}pt{status_text}"
                draw.text((pix.width - 120, ideal_y_px - 8), label, fill=color)
        
        margin_data = get_page_margin(page)
        if margin_data:
            info = f"Margin aktual: Kiri={pt_to_cm(margin_data['left']):.2f}cm, Kanan={pt_to_cm(margin_data['right']):.2f}cm, Atas={pt_to_cm(margin_data['top']):.2f}cm, Bawah={pt_to_cm(margin_data['bottom']):.2f}cm"
            draw.text((10, 30), info, fill=(0, 0, 0))
            draw.text((10, 50), f"Sumber: {margin_data.get('source', 'unknown')}", fill=(0, 0, 0))
        
        draw.text((10, 70), "Garis biru = posisi ideal baris berikutnya (18 pt) | Hijau=OK, Oranye=extra space, Merah=terlalu rapat", fill=(0, 0, 0))
        draw.text((10, 90), "Gap >30 pt dianggap antar paragraf (bukan error line spacing)", fill=(0, 0, 0))
        draw.text((10, pix.height - 30), f"Halaman {page_num}", fill=(0, 0, 0))
        
        doc.close()
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        return img_bytes.getvalue()
        
    except Exception as e:
        print(f"Error rendering page: {e}")
        return None

# ========== ANALYZE PAGE DEVIATIONS ==========
def analyze_page_deviations(file_bytes, page_num):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if page_num < 1 or page_num > len(doc):
            return None
        
        page = doc[page_num - 1]
        width_pt = page.rect.width
        height_pt = page.rect.height
        
        margin_data = get_page_margin(page)
        if margin_data is None:
            margin_data = {'left': 0, 'right': 0, 'top': 0, 'bottom': 0, 'source': 'none'}
        target_margin_pt = cm_to_pt(3.0)
        
        margin_status = {}
        margin_deviations_cm = {}
        for side in ['left', 'right', 'top', 'bottom']:
            actual = margin_data[side]
            dev_cm = round(pt_to_cm(actual - target_margin_pt), 2)
            margin_deviations_cm[side] = dev_cm
            if actual < target_margin_pt - 0.2:
                margin_status[side] = f"MELEWATI BATAS (deviasi {dev_cm:+.2f} cm)"
            else:
                margin_status[side] = f"AMAN (deviasi {dev_cm:+.2f} cm)"
        
        lines = get_lines_with_positions(page)
        spacing_deviations = []
        for i in range(len(lines) - 1):
            gap = lines[i+1]['y0'] - lines[i]['y0']
            if 0 < gap < 200:
                if gap > 30:
                    status = "ANTAR PARAGRAF"
                    is_ok = True
                elif gap < 6:
                    status = "TERLALU RAPAT"
                    is_ok = False
                else:
                    is_ok = True
                    status = "OK"
                spacing_deviations.append({
                    'line': i + 1,
                    'gap_pt': round(gap, 1),
                    'deviation_pt': round(gap - 18, 1),
                    'status': status,
                    'is_ok': is_ok
                })
        
        left_margin = margin_data['left']
        right_margin = margin_data['right']
        effective_width = width_pt - left_margin - right_margin
        tolerance = 5
        
        justify_count = 0
        total_valid = 0
        for line in lines:
            if len(line['words']) < 3:
                continue
            total_valid += 1
            line_width = line['x1'] - line['x0']
            if (line_width > 0.80 * effective_width and
                abs(line['x1'] - (width_pt - right_margin)) <= tolerance):
                justify_count += 1
        
        justify_percentage = (justify_count / total_valid * 100) if total_valid > 0 else 0
        justify_ok = justify_percentage >= 40
        
        doc.close()
        
        return {
            'margin_status': margin_status,
            'margin_deviations_cm': margin_deviations_cm,
            'actual_margins_cm': {
                'left': round(pt_to_cm(margin_data['left']), 2),
                'right': round(pt_to_cm(margin_data['right']), 2),
                'top': round(pt_to_cm(margin_data['top']), 2),
                'bottom': round(pt_to_cm(margin_data['bottom']), 2)
            },
            'margin_source': margin_data.get('source', 'unknown'),
            'spacing_deviations': spacing_deviations,
            'justify_percentage': round(justify_percentage, 1),
            'justify_ok': justify_ok
        }
    except Exception as e:
        return {'error': str(e)}

# ========== FORMAT VALIDATION ==========
def analyze_pdf_format(file_bytes, min_words=2000, max_words=3000):
    info = get_pdf_detailed_info(file_bytes)
    if 'error' in info:
        return {'error': info['error']}
    
    text = extract_text_from_pdf(file_bytes)
    
    # === EKSTRAK TEKS UTAMA (SEBELUM DAFTAR PUSTAKA & LAMPIRAN) ===
    main_text = extract_text_before_excluded_sections(text)
    main_word_count = len(main_text.split())
    
    # Deteksi apakah ada bagian yang dikecualikan
    excluded_start = find_excluded_section_start(text)
    excluded_detected = excluded_start is not None
    
    # === UKURAN KERTAS ===
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
    
    # === MARGIN ===
    target_margin_cm = 3.0
    margin_tolerance_cm = 0.2
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
        if p['word_count'] < 50:
            ok = True
        else:
            ok = all(v >= target_margin_cm - margin_tolerance_cm for v in margins_cm.values())
        margin_details.append({
            'page': p['page'],
            'margins_cm': margins_cm,
            'margins_pt': {'top': m['top'], 'bottom': m['bottom'], 'left': m['left'], 'right': m['right']},
            'ok': ok,
            'word_count': p['word_count'],
            'source': m.get('source', 'unknown')
        })
        if not ok:
            margin_ok = False
    
    # === FONT ===
    all_fonts = info['all_fonts']
    non_times = {f: c for f, c in all_fonts.items() if not ('Times' in f or 'TimesNewRoman' in f)}
    font_ok = len(non_times) == 0
    
    # === UKURAN FONT ===
    all_sizes = info.get('all_sizes', [])
    avg_font_size = statistics.mean(all_sizes) if all_sizes else 0
    font_size_ok = 11.0 <= avg_font_size <= 13.0 if avg_font_size > 0 else False
    
    # === SPASI ===
    spacing_details = []
    spacing_ok = True
    for p in info['page_data']:
        s = p['spacing_info']
        is_ok = 6 <= s['spacing'] <= 30
        spacing_details.append({
            'page': p['page'],
            'spacing_pt': s['spacing'],
            'spacing_cm': pt_to_cm(s['spacing']) if s['spacing'] > 0 else 0,
            'is_1_5': is_ok,
            'details': s['details']
        })
        if not is_ok:
            spacing_ok = False
    
    # === JUSTIFY ===
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
    
    # === JUMLAH KATA ===
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
        'excluded_sections_detected': excluded_detected,
        'all_ok': all_ok
    }
