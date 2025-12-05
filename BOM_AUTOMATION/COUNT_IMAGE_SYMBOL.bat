@echo off
echo ========================================
echo SYMBOL COUNTING TOOL
echo ========================================
echo.
echo Counting symbol: image.png
echo PDF: H.pdf
echo.

.\bom\Scripts\python.exe count_symbol.py H.pdf image.png --thresh 0.65 --dpi 300

echo.
echo ========================================
echo Done! Check outputs\symbol_count_*.json for detailed results
echo ========================================
pause

