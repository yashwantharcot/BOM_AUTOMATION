# OpenCV Installation Guide - Windows DLL Fix

## Current Status
OpenCV installation is failing due to missing Visual C++ runtime DLLs.

## Solution Steps

### Step 1: Install Visual C++ Redistributable (REQUIRED)

The installer returned code **3010** which means **RESTART REQUIRED**.

**Option A: Manual Installation**
1. Run: `config\vc_redist.x64.exe`
2. Follow the installer prompts
3. **RESTART YOUR COMPUTER** (important!)
4. After restart, test OpenCV again

**Option B: Download Latest Version**
1. Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Run the installer
3. **RESTART YOUR COMPUTER**
4. Test OpenCV

### Step 2: After Restart, Install OpenCV

```bash
# Uninstall any existing versions
pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python

# Install fresh
pip install opencv-python

# Test
python -c "import cv2; print('OpenCV version:', cv2.__version__)"
```

### Step 3: If Still Not Working

Try these alternatives:

**Option 1: Install opencv-contrib-python**
```bash
pip install opencv-contrib-python
```

**Option 2: Install older stable version**
```bash
pip install opencv-python==4.8.1.78
```

**Option 3: Use Anaconda/Miniconda**
```bash
conda install -c conda-forge opencv
```

**Option 4: Manual DLL Fix**
1. Download OpenCV pre-built binaries from: https://opencv.org/releases/
2. Extract to a folder
3. Add `opencv\build\x64\vc16\bin` to your system PATH
4. Restart terminal

## Quick Test After Installation

```bash
python -c "import cv2; print('OpenCV', cv2.__version__, 'is working!')"
```

## Expected Output
```
OpenCV 4.x.x is working!
```

## Once OpenCV Works

Run the symbol detection test:
```bash
python test_symbol_count_fixed.py
```

## Common Issues

1. **DLL load failed**: VC++ Redistributable not installed or restart needed
2. **Module not found**: OpenCV not installed correctly
3. **Version mismatch**: Python architecture (32-bit vs 64-bit) mismatch

## Verification

After fixing, verify with:
```python
import cv2
import numpy as np

# Test basic functionality
img = np.zeros((100, 100, 3), dtype=np.uint8)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print("OpenCV is working correctly!")
```




