@echo off
echo ========================================
echo Streamlit Symbol Extraction UI
echo ========================================
echo.
echo Starting Streamlit app...
echo.
echo The app will open in your default browser.
echo If not, navigate to: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server.
echo.
echo ========================================
echo.

.\bom\Scripts\python.exe -m streamlit run streamlit_symbol_extraction.py

pause

