@echo off
echo ========================================
echo Symbol Extraction FastAPI Server
echo ========================================
echo.
echo Starting server on http://127.0.0.1:8001
echo.
echo Endpoints:
echo   POST /extract - Upload PDF to extract symbols
echo   POST /extract/local - Extract from PDF in uploads folder
echo   GET /health - Health check
echo   GET /docs - Interactive API documentation
echo.
echo Example usage:
echo   curl -X POST "http://127.0.0.1:8001/extract/local" ^
echo     -F "pdf_filename=H.pdf" ^
echo     -F "min_count=2" ^
echo     -F "include_images=true"
echo.
echo ========================================
echo.

.\bom\Scripts\python.exe api/fastapi_symbol_extraction.py

pause

