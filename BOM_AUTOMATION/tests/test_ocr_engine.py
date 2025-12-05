from extractors.ocr_engine import ocr_image_pil


def test_ocr_engine_no_tesseract():
    # Without tesseract installed, the function should return an empty list
    res = ocr_image_pil(None)
    assert isinstance(res, list)
    assert res == []
