# Repair or Replace Advisor - PowerShell Launcher
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     Repair or Replace Advisor - Local Development" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " [1] Start Full Stack via Docker Compose (Recommended)" -ForegroundColor Green
Write-Host " [2] Start React Frontend Dev Server (http://localhost:3000)" -ForegroundColor Yellow
Write-Host " [3] Start FastAPI Backend Server (http://localhost:8000)" -ForegroundColor Magenta
Write-Host " [4] Build Production Frontend Bundle (Vite)" -ForegroundColor Blue
Write-Host " [5] Exit"
Write-Host ""

$choice = Read-Host "Select an option [1-5]"

switch ($choice) {
    "1" {
        Write-Host "Starting Docker Compose..." -ForegroundColor Green
        docker-compose up --build
    }
    "2" {
        Write-Host "Starting Frontend Dev Server on http://localhost:3000..." -ForegroundColor Yellow
        Set-Location frontend
        npm run dev
    }
    "3" {
        Write-Host "Starting Backend on http://localhost:8000..." -ForegroundColor Magenta
        if (Get-Command uvicorn -ErrorAction SilentlyContinue) {
            uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        } else {
            & "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0\python3.12.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        }
    }
    "4" {
        Write-Host "Building Vite production assets..." -ForegroundColor Blue
        Set-Location frontend
        npm run build
    }
    Default {
        Write-Host "Exiting."
    }
}
