from .pdf_parser import analyze_pdf_format, detect_bibliography, extract_text_from_pdf

def validate_pdf(file_bytes, min_words=2000, max_words=3000):
    """Validasi PDF dan kembalikan detail"""
    return analyze_pdf_format(file_bytes, min_words, max_words)