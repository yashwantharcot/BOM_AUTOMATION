@echo off
REM Quick start script for simple symbol detection test

echo ======================================================================
echo Simple Symbol Detection Test
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
echo Running test...
echo ======================================================================
echo.

python test_symbol_simple.py

echo.
pause





