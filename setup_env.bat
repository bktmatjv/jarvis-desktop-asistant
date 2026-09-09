@echo off
chcp 65001 > nul
title JARVIS Setup ^& Diagnostic

echo ====================================================
echo        INSTALADOR Y DIAGNÓSTICO DE JARVIS
echo ====================================================

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if not exist "venv" (
    echo [1/4] Creando entorno virtual 'venv'...
    python -m venv venv
) else (
    echo [1/4] Entorno virtual 'venv' detectado.
)

echo [2/4] Instalando dependencias de Backend...
call venv\Scripts\pip.exe install -r backend\requirements.txt

echo [3/4] Instalando dependencias de Cliente...
call venv\Scripts\pip.exe install -r client\requirements.txt

if not exist "client\model" (
    echo [4/4] Descargando modelo de Vosk para Wake Word offline...
    venv\Scripts\python.exe client\download_model.py
) else (
    echo [4/4] Modelo de Vosk verificado en client\model.
)

if not exist ".env" (
    echo.
    echo [AVISO]: No existe archivo .env. Creando a partir de .env.example...
    copy .env.example .env
    echo Por favor edita el archivo .env con tus claves de Groq y MongoDB.
)

echo.
echo ====================================================
echo  ¡INSTALACIÓN COMPLETADA CON ÉXITO!
echo  Para iniciar JARVIS, ejecuta start_jarvis.bat
echo ====================================================
pause
