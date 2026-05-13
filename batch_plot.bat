@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Maxwell CSV Batch Plotter — drag files/folders onto this .bat file
:: Or double-click to process all CSVs in the current folder

cd /d "%~dp0"

set PYTHON=C:\All_In_All\AppInstall\Anaconda3\python.exe
if not exist "%PYTHON%" set PYTHON=python

set ARGS=
if "%~1"=="" (
    :: No files dragged — process all CSVs in test_data folder
    set ARGS=test_data
) else (
    :: Files/folders dragged — collect all arguments
    :loop
    if "%~1"=="" goto :process
    set ARGS=!ARGS! "%~1"
    shift
    goto :loop
)

:process
echo ========================================
echo   Maxwell CSV Batch Plotter
echo   Processing: !ARGS!
echo ========================================
echo.

"%PYTHON%" main.py --batch !ARGS! --output output

echo.
echo Press any key to exit...
pause >nul
