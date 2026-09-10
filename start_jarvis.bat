@echo off
chcp 65001 > nul
title JARVIS Launcher

echo ====================================================
echo           INICIANDO SISTEMA JARVIS 2.5
echo ====================================================

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encontró el entorno virtual 'venv'.
    echo Por favor ejecuta setup_env.bat primero.
    pause
    exit /b 1
)

echo [1/3] Iniciando Servidor Backend FastAPI en segundo plano...
start "JARVIS Backend Server" /min "%PROJECT_DIR%venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

echo [2/3] Esperando que el servidor esté en línea...
:check_backend
timeout /t 2 /nobreak > nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" > nul 2>&1
if errorlevel 1 (
    echo       Servidor conectando...
    goto check_backend
)

echo [3/3] Servidor conectado exitosamente. Lanzando Cliente HUD...
echo Presiona Ctrl+Espacio para el Orbe, y Ctrl+Flecha Arriba para el Panel.
"%PROJECT_DIR%venv\Scripts\python.exe" client\main.py

echo.
echo ====================================================
echo Cerrando JARVIS y deteniendo servicios en background...
echo ====================================================
taskkill /FI "WINDOWTITLE eq JARVIS Backend Server*" /F > nul 2>&1

echo JARVIS detenido correctamente.
