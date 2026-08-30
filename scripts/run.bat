@echo off
cd /d "%~dp0\.."
cls
echo ==================================================
echo           IMAGE GRID SLICER ^& ANIMATOR         
echo ==================================================
echo.

if exist env\Scripts\python.exe (
    set "PYTHON_BIN=env\Scripts\python.exe"
    echo [OK] Using virtual environment: env
) else if exist venv\Scripts\python.exe (
    set "PYTHON_BIN=venv\Scripts\python.exe"
    echo [OK] Using virtual environment: venv
) else (
    set "PYTHON_BIN=python"
    echo [OK] Using system python
)

%PYTHON_BIN% -c "import PIL, numpy" >nul 2>&1
if errorlevel 1 (
    echo [..] Installing dependencies...
    %PYTHON_BIN% -m pip install -r requirements.txt
)

echo.
echo Launching Image Grid Slicer...
echo.
%PYTHON_BIN% slice_image.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] App exited with an error.
    pause
)
