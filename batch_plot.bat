@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: Find Python — try PATH first, then common locations
set PYTHON=
where python >nul 2>nul && set PYTHON=python
if "!PYTHON!"=="" if exist "C:\All_In_All\AppInstall\Anaconda3\python.exe" set PYTHON=C:\All_In_All\AppInstall\Anaconda3\python.exe
if "!PYTHON!"=="" if exist "C:\ProgramData\anaconda3\python.exe" set PYTHON=C:\ProgramData\anaconda3\python.exe
if "!PYTHON!"=="" if exist "%USERPROFILE%\anaconda3\python.exe" set PYTHON=%USERPROFILE%\anaconda3\python.exe
if "!PYTHON!"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if "!PYTHON!"=="" (
    echo [ERROR] Python not found. Please install Python or Anaconda.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Maxwell CSV Batch Plotter
echo ========================================
echo   Python: !PYTHON!
echo.

:: Collect input paths
set FILE_COUNT=0
set INPUTS=
if not "%~1"=="" (
    :: Files/folders dragged onto .bat
    :loop
    if "%~1"=="" goto :process
    set INPUTS=!INPUTS! "%~1"
    set /a FILE_COUNT+=1
    shift
    goto :loop
) else (
    :: Double-clicked — process test_data folder
    echo   No files dragged. Processing test_data/ ...
    set INPUTS=test_data
)

:process
echo   Input: !INPUTS!
echo   Output: output\
echo.

"!PYTHON!" main.py --batch !INPUTS! --output output

echo.
echo ========================================
echo   Done! Files saved to output\
echo ========================================
echo.
echo You can close this window or press any key.
pause >nul
