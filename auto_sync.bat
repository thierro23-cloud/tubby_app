@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM AUTO_SYNC.BAT
REM ------------------------------------------------------------
REM Autor: Tinito
REM Fecha: 2026-07-07
REM ------------------------------------------------------------
REM INTRODUCCIÓN:
REM Este script automatiza la sincronización de un repositorio Git
REM local con GitHub (nube). Su objetivo es mantener actualizados
REM los archivos del ordenador y del repositorio remoto.
REM
REM EXPLICACIÓN GENERAL:
REM 1) Entra a la carpeta del repositorio.
REM 2) Verifica que la carpeta sea un repo Git válido.
REM 3) Agrega cambios (git add -A).
REM 4) Si hay cambios, crea commit automático con fecha/hora.
REM 5) Trae cambios remotos con rebase (git pull --rebase).
REM 6) Sube cambios al remoto (git push).
REM 7) Guarda todo en un archivo de log para auditoría.
REM
REM NOTAS IMPORTANTES:
REM - Si hay conflictos, el script se detiene para evitar daños.
REM - Si no hay cambios locales, no crea commit vacío.
REM - Recomendado ejecutarlo con el Programador de tareas.
REM ============================================================

REM --- CONFIGURACIÓN PRINCIPAL ---
set REPO_DIR=C:\Users\thier\Desktop\tubby_app
set LOG_FILE=%REPO_DIR%\auto_sync.log
set BRANCH=main
set REMOTE=origin

REM --- Inicio de ejecución: separador en log ---
echo ==================================================>> "%LOG_FILE%"
echo [%date% %time%] Iniciando auto-sync...>> "%LOG_FILE%"

REM --- Paso 1: entrar al directorio del repositorio ---
cd /d "%REPO_DIR%" || (
  echo [%date% %time%] ERROR: No se pudo entrar al repo.>> "%LOG_FILE%"
  exit /b 1
)

REM --- Paso 2: validar que sea repositorio Git ---
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR: Esta carpeta no es un repositorio Git.>> "%LOG_FILE%"
  exit /b 1
)

REM --- Paso 3: agregar todos los cambios (nuevos, editados, borrados) ---
echo [%date% %time%] git add -A>> "%LOG_FILE%"
git add -A >> "%LOG_FILE%" 2>&1

REM --- Paso 4: comprobar si hay cambios en staging para commit ---
git diff --cached --quiet
if errorlevel 1 (
  REM Hay cambios: crear commit automático con sello de fecha y hora
  set MSG=auto-sync %date% %time%
  echo [%date% %time%] git commit -m "!MSG!">> "%LOG_FILE%"
  git commit -m "!MSG!" >> "%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [%date% %time%] ERROR: Fallo en commit.>> "%LOG_FILE%"
    exit /b 1
  )
) else (
  REM No hay cambios: no crear commit vacío
  echo [%date% %time%] Sin cambios para commit.>> "%LOG_FILE%"
)

REM --- Paso 5: traer cambios de GitHub antes de subir (rebase) ---
echo [%date% %time%] git pull --rebase %REMOTE% %BRANCH%>> "%LOG_FILE%"
git pull --rebase %REMOTE% %BRANCH% >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR: Fallo en pull --rebase (posible conflicto).>> "%LOG_FILE%"
  exit /b 1
)

REM --- Paso 6: subir cambios al remoto ---
echo [%date% %time%] git push %REMOTE% %BRANCH%>> "%LOG_FILE%"
git push %REMOTE% %BRANCH% >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR: Fallo en push.>> "%LOG_FILE%"
  exit /b 1
)

REM --- Fin exitoso ---
echo [%date% %time%] OK: Auto-sync completado.>> "%LOG_FILE%"
exit /b 0