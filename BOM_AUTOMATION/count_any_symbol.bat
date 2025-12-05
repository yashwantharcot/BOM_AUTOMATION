@echo off
REM Count any symbol template
REM Usage: count_any_symbol.bat <symbol_template_path>
REM Example: count_any_symbol.bat outputs\vector_symbols\symbol_ccbeffb7_count1.png

if "%~1"=="" (
    echo Usage: count_any_symbol.bat ^<symbol_template_path^>
    echo Example: count_any_symbol.bat outputs\vector_symbols\symbol_ccbeffb7_count1.png
    pause
    exit /b 1
)

echo ========================================
echo SYMBOL COUNTING TOOL
echo ========================================
echo.
echo PDF: H.pdf
echo Symbol Template: %~1
echo.

.\bom\Scripts\python.exe count_symbol.py H.pdf "%~1" --thresh 0.65 --dpi 300

echo.
echo ========================================
echo Done! Check outputs\symbol_count_*.json for detailed results
echo ========================================
pause

