import os
from extractors.vector_text_extractor import extract_vector_text


def test_extract_vector_text_no_fitz():
    # If fitz not installed, function should return an empty list and not crash
    res = extract_vector_text('nonexistent.pdf')
    assert isinstance(res, list)
    assert res == [] or all(isinstance(p, list) for p in res)
