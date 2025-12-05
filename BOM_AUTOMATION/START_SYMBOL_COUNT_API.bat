@echo off
echo ========================================
echo Symbol Counting FastAPI Server
echo ========================================
echo.
echo Starting server on http://127.0.0.1:8000
echo.
echo Endpoints:
echo   POST /count - Upload PDF and symbol template
echo   POST /count/local - Use files from uploads folder
echo   GET /health - Health check
echo   GET /docs - API documentation (Swagger UI)
echo.
echo Example usage:
echo   curl -X POST "http://127.0.0.1:8000/count/local" ^
echo     -F "pdf_filename=H.pdf" ^
echo     -F "symbol_filename=image.png" ^
echo     -F "threshold=0.65" ^
echo     -F "dpi=300"
echo.
echo ========================================
echo.

.\bom\Scripts\python.exe api/fastapi_symbol_count.py

pause

