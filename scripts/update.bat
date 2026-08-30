@echo off
cd /d "%~dp0\.."
cls
echo ==================================================
echo            UPDATING IMAGE GRID SLICER          
echo ==================================================
echo.

git pull
echo.
if exist env\Scripts\python.exe (
    env\Scripts\python.exe -m pip install -r requirements.txt
) else if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
    python -m pip install -r requirements.txt
)

echo.
echo ==================================================
echo Update Complete!
echo ==================================================
pause
