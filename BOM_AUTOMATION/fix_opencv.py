#!/usr/bin/env python3
"""
OpenCV DLL Fix Diagnostic and Solution Script
"""

import sys
import os
import subprocess
from pathlib import Path

def check_opencv():
    """Check OpenCV status"""
    print("=" * 70)
    print("OpenCV Diagnostic Tool")
    print("=" * 70)
    
    try:
        import cv2
        print(f"[OK] OpenCV is working!")
        print(f"     Version: {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"[ERROR] OpenCV import failed: {e}")
        return False

def find_opencv_dlls():
    """Find OpenCV DLL location"""
    try:
        import site
        site_packages = site.getsitepackages()[0]
        cv2_path = Path(site_packages) / "cv2"
        
        if cv2_path.exists():
            print(f"\n[*] OpenCV installed at: {cv2_path}")
            dll_files = list(cv2_path.glob("*.dll"))
            if dll_files:
                print(f"[*] Found {len(dll_files)} DLL files")
                for dll in dll_files[:5]:
                    print(f"    - {dll.name}")
            else:
                print("[WARN] No DLL files found in cv2 directory")
            
            # Check for .pyd files
            pyd_files = list(cv2_path.glob("*.pyd"))
            if pyd_files:
                print(f"[*] Found {len(pyd_files)} .pyd files")
        else:
            print("[ERROR] cv2 directory not found")
    except Exception as e:
        print(f"[ERROR] Could not locate OpenCV: {e}")

def install_vcredist():
    """Try to install VC++ Redistributable"""
    vcredist_path = Path("config/vc_redist.x64.exe")
    
    if vcredist_path.exists():
        print(f"\n[*] Found VC++ Redistributable: {vcredist_path}")
        print("[*] Attempting to install...")
        try:
            # Try silent install
            result = subprocess.run(
                [str(vcredist_path), "/install", "/quiet", "/norestart"],
                capture_output=True,
                timeout=60
            )
            if result.returncode == 0:
                print("[OK] VC++ Redistributable installed successfully")
                return True
            else:
                print(f"[WARN] Install returned code: {result.returncode}")
                print("[INFO] You may need to run the installer manually")
                return False
        except Exception as e:
            print(f"[ERROR] Install failed: {e}")
            print("[INFO] Please run config/vc_redist.x64.exe manually")
            return False
    else:
        print("[WARN] VC++ Redistributable installer not found")
        print("[INFO] Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        return False

def try_opencv_workaround():
    """Try workaround solutions"""
    print("\n" + "=" * 70)
    print("Trying Workaround Solutions")
    print("=" * 70)
    
    solutions = [
        {
            "name": "Install opencv-contrib-python",
            "command": ["pip", "install", "--upgrade", "opencv-contrib-python"],
            "description": "Contrib version sometimes has better DLL support"
        },
        {
            "name": "Install specific OpenCV version with bundled DLLs",
            "command": ["pip", "install", "opencv-python==4.5.5.64"],
            "description": "Older version with bundled dependencies"
        }
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"\n[{i}/{len(solutions)}] {solution['name']}")
        print(f"    {solution['description']}")
        response = input("    Try this? (y/n): ").strip().lower()
        
        if response == 'y':
            try:
                print(f"    Running: {' '.join(solution['command'])}")
                result = subprocess.run(solution['command'], capture_output=True, text=True)
                print(result.stdout)
                if result.returncode == 0:
                    print("    [OK] Installation complete")
                    if check_opencv():
                        print("    [SUCCESS] OpenCV is now working!")
                        return True
                else:
                    print(f"    [ERROR] Installation failed: {result.stderr}")
            except Exception as e:
                print(f"    [ERROR] {e}")
    
    return False

def main():
    print("\n[*] Checking OpenCV status...")
    if check_opencv():
        print("\n[SUCCESS] OpenCV is already working!")
        return
    
    find_opencv_dlls()
    
    print("\n[*] Checking VC++ Redistributable...")
    install_vcredist()
    
    # Wait a moment for DLL registration
    import time
    print("\n[*] Waiting 3 seconds for DLL registration...")
    time.sleep(3)
    
    if check_opencv():
        print("\n[SUCCESS] OpenCV is now working!")
        return
    
    print("\n" + "=" * 70)
    print("OpenCV still not working. Trying workarounds...")
    print("=" * 70)
    
    if not try_opencv_workaround():
        print("\n" + "=" * 70)
        print("Manual Fix Required")
        print("=" * 70)
        print("\nPlease try the following:")
        print("1. Run config/vc_redist.x64.exe manually (if it exists)")
        print("2. Download and install VC++ Redistributable from:")
        print("   https://aka.ms/vs/17/release/vc_redist.x64.exe")
        print("3. Restart your computer")
        print("4. Try: pip install --upgrade --force-reinstall opencv-python")
        print("\nOr use the workaround: Install Anaconda/Miniconda which includes")
        print("all required DLLs, then install opencv-python in that environment.")

if __name__ == '__main__':
    main()





