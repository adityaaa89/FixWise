@echo off
title Repair or Replace Advisor Launcher
cls
echo ============================================================
echo      Repair or Replace Advisor - Local Development
echo ============================================================
echo.
echo  [1] Start Full Stack via Docker Compose (Recommended)
echo  [2] Start React Frontend Dev Server (http://localhost:3000)
echo  [3] Start FastAPI Backend Server (http://localhost:8000)
echo  [4] Build Production Frontend Bundle (Vite)
echo  [5] Exit
echo.
set /p choice="Select an option [1-5]: "

if "%choice%"=="1" (
    echo.
    echo Starting Docker Compose...
    docker-compose up --build
    goto end
)
if "%choice%"=="2" (
    echo.
    echo Starting Frontend Dev Server on http://localhost:3000 ...
    cd frontend
    npm run dev
    goto end
)
if "%choice%"=="3" (
    echo.
    echo Starting Backend on http://localhost:8000 ...
    where uvicorn >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    ) else (
        where python >nul 2>nul
        if %ERRORLEVEL% EQU 0 (
            python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        ) else (
            "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0\python3.12.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        )
    )
    goto end
)
if "%choice%"=="4" (
    echo.
    echo Building Vite production assets...
    cd frontend
    npm run build
    goto end
)
if "%choice%"=="5" (
    exit /b 0
)

:end
pause
