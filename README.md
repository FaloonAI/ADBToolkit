# ADB Toolkit 
![adb_toolkit]()

<a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/mashape/apistatus.svg"></a>  
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)  
[![Platform](https://img.shields.io/badge/Windows-10/11+-0078D6?logo=windows)](https://www.microsoft.com/windows)  


## About the Project
**ADB Toolkit** is a multifunctional Python-based tool for automated control of Android devices via ADB and scrcpy.

*This tool is designed for **Windows only***.

**Key Features**:
- Control Android devices over USB
- Automatic device detection
- Screen mirroring via `scrcpy`
- Modular architecture support
- Lightweight and intuitive console interface

---

## Requirements (Windows only)

### 1. Install ADB (Android Debug Bridge)
- Download Android Platform Tools:  
  [https://developer.android.com/tools/releases/platform-tools](https://developer.android.com/tools/releases/platform-tools)
- Extract the archive and add the folder path to your **System PATH**  
  (e.g., `C:\platform-tools`)

### 2. Install `scrcpy` (for screen mirroring)
- Download the latest version of scrcpy:  
  [https://github.com/Genymobile/scrcpy/releases](https://github.com/Genymobile/scrcpy/releases)
- Extract the folder and add it to your **System PATH**

Make sure you can run `adb` and `scrcpy` from the terminal (CMD/PowerShell).

---

## Quick Start

### 3. Clone the project and install dependencies
```bash
git clone 
cd ADB_Toolkit
pip install -r requirements.txt
python adb_toolkit.py
```
