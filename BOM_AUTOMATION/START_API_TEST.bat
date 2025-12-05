@echo off
REM Quick start script for API test on Windows

echo ======================================================================
echo Symbol Detection API Test
echo ======================================================================
echo.

REM Check if OpenCV is installed
python -c "import cv2; print('OpenCV version:', cv2.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] OpenCV not installed!
    echo.
    echo Installing OpenCV...
    pip install opencv-python-headless
    echo.
)

echo.
echo Starting API server on http://localhost:5001
echo Press Ctrl+C to stop
echo.
echo ======================================================================
echo.

python api/test_symbol_detection_api.py

pause





