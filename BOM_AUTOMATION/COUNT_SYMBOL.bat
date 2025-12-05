@echo off
echo ========================================
echo SYMBOL COUNTING TOOL
echo ========================================
echo.
echo Counting symbol: outputs\vector_symbols\symbol_ccbeffb7_count1.png
echo.

.\bom\Scripts\python.exe count_symbol.py H.pdf outputs\vector_symbols\symbol_ccbeffb7_count1.png --thresh 0.65 --dpi 300

echo.
echo ========================================
echo Done! Check outputs\symbol_count_*.json for detailed results
echo ========================================
pause

