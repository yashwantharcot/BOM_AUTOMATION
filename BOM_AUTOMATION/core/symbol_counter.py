#!/usr/bin/env python3
"""
PDF Symbol Counter - Analyzes and counts symbols in a PDF file.
Supports both text-based and scanned PDFs.
"""

import sys
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2", "pdfplumber", "pytesseract", "pillow"])
    import PyPDF2

try:
    import pdfplumber
except ImportError:
    pass

try:
    from PIL import Image
    import pytesseract
except ImportError:
    pass

import re
from collections import Counter, defaultdict


def count_symbols_text_pdf(pdf_path):
    """Extract and count symbols from text-based PDF."""
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_path}")
    print(f"{'='*60}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Total pages: {total_pages}")
            
            all_text = ""
            page_details = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                all_text += text
                page_details.append({
                    'page': page_num,
                    'text': text,
                    'char_count': len(text)
                })
            
            return analyze_symbols(all_text, page_details)
    
    except Exception as e:
        print(f"Error reading text-based PDF: {e}")
        return None


def analyze_symbols(text, page_details=None):
    """Analyze and count various types of symbols."""
    print(f"\n{'='*60}")
    print("SYMBOL ANALYSIS")
    print(f"{'='*60}")
    
    results = {
        'total_characters': len(text),
        'total_words': len(text.split()),
        'symbols': {}
    }
    
    # Count all characters
    char_counter = Counter(text)
    
    # Categorize symbols
    symbol_categories = {
        'alphanumeric': r'[a-zA-Z0-9]',
        'spaces_newlines': r'[\s\n\r\t]',
        'punctuation': r'[.,;:\'"!?()[\]{}]',
        'mathematical': r'[+\-*/=<>±×÷∑∏∫√∞]',
        'special_chars': r'[@#$%&*^~`|\\]',
        'brackets': r'[(){}\[\]]',
        'quotes': r'["\'\`]',
        'dashes_hyphens': r'[-–—−]',
        'arrows_symbols': r'[→←↑↓↖↗↙↘⟹⟸]',
        'other': r'[^\w\s.,;:\'"!?()[\]{}@#$%&*^~`|\\+\-*/=<>±×÷∑∏∫√∞→←↑↓↖↗↙↘⟹⟸\n\r\t-]'
    }
    
    # Count by category
    for category, pattern in symbol_categories.items():
        matches = re.findall(pattern, text)
        count = len(matches)
        if count > 0:
            results['symbols'][category] = {
                'count': count,
                'percentage': (count / len(text) * 100) if len(text) > 0 else 0
            }
    
    # Top 20 most common characters
    print(f"\nTotal Characters: {results['total_characters']:,}")
    print(f"Total Words: {results['total_words']:,}")
    
    print(f"\n{'Symbol Category':<25} {'Count':>12} {'Percentage':>12}")
    print("-" * 50)
    for category, data in sorted(results['symbols'].items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"{category:<25} {data['count']:>12,} {data['percentage']:>11.2f}%")
    
    print(f"\n{'='*60}")
    print("TOP 30 MOST COMMON CHARACTERS")
    print(f"{'='*60}")
    print(f"{'Char':<8} {'Count':>10} {'Percentage':>12} {'Unicode':>12}")
    print("-" * 45)
    
    for char, count in char_counter.most_common(30):
        percentage = (count / len(text) * 100) if len(text) > 0 else 0
        # Format char display (handle special characters)
        char_display = repr(char)[1:-1] if char in '\n\r\t ' else char
        try:
            unicode_val = f"U+{ord(char):04X}"
        except:
            unicode_val = "N/A"
        print(f"{char_display:<8} {count:>10,} {percentage:>11.2f}% {unicode_val:>12}")
    
    # Specific symbol counts
    print(f"\n{'='*60}")
    print("SPECIFIC SYMBOL COUNTS")
    print(f"{'='*60}")
    
    specific_symbols = {
        'Spaces': ' ',
        'Newlines': '\n',
        'Tabs': '\t',
        'Periods': '.',
        'Commas': ',',
        'Colons': ':',
        'Semicolons': ';',
        'Hyphens': '-',
        'Underscores': '_',
        'Parentheses (': '(',
        'Parentheses )': ')',
        'Square Brackets [': '[',
        'Square Brackets ]': ']',
        'Curly Braces {': '{',
        'Curly Braces }': '}',
        'Quotes "': '"',
        'Apostrophes': "'",
        'Slashes /': '/',
        'Backslashes': '\\',
        'At Signs': '@',
        'Hash/Pound': '#',
        'Dollar Signs': '$',
        'Percent': '%',
        'Ampersands': '&',
        'Asterisks': '*',
        'Plus Signs': '+',
        'Equals': '=',
        'Question Marks': '?',
        'Exclamation': '!',
        'Pipe |': '|',
    }
    
    for label, symbol in specific_symbols.items():
        count = text.count(symbol)
        if count > 0:
            print(f"{label:<25} {count:>10,}")
    
    # Page-by-page breakdown
    if page_details:
        print(f"\n{'='*60}")
        print("PAGE-BY-PAGE BREAKDOWN")
        print(f"{'='*60}")
        print(f"{'Page':<8} {'Characters':>15} {'Words':>15}")
        print("-" * 40)
        for page_info in page_details:
            words = len(page_info['text'].split()) if page_info['text'] else 0
            print(f"{page_info['page']:<8} {page_info['char_count']:>15,} {words:>15,}")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python symbol_counter.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    results = count_symbols_text_pdf(pdf_path)
    
    if results:
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}\n")
    else:
        print("Could not analyze PDF")
        sys.exit(1)


if __name__ == "__main__":
    main()
