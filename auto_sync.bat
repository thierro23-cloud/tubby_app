@echo off
setlocal enabledelayedexpansion

REM ================================================================================
REM ARCHIVO: auto_sync.bat
REM AUTOR: Tinito
REM FECHA: 2026-07-07
REM ================================================================================
REM INTRODUCCIÓN
REM ------------------------------------------------------------------------------
REM Este script automatiza la sincronización entre tu carpeta local (ordenador)
REM y GitHub (nube) para la rama principal.
REM
REM OBJETIVO
REM ------------------------------------------------------------------------------
REM - Si detecta cambios remotos en GitHub, los baja al ordenador.
REM - Si detecta cambios locales en el ordenador, los sube a GitHub.
REM - Si NO hay cambios (ni locales ni remotos), no hace nada.
REM
REM CÓMO FUNCIONA (RESUMEN)
REM ------------------------------------------------------------------------------
REM 1) Entra al repositorio local.
REM 2) Hace "git fetch" para consultar si la nube cambió.
REM 3) Detecta si origin/main va por delante de HEAD local.
REM 4) Detecta si hay cambios locales sin commit.
REM 5) Si no hay cambios en ningún lado, termina.
REM 6) Si hay cambios remotos, ejecuta pull --rebase.
REM 7) Si hay cambios locales, hace commit y push.
REM 8) Guarda registro en auto_sync.log.
REM
REM IMPORTANTE
REM ------------------------------------------------------------------------------
REM - Debes tener en .gitignore esta línea:
REM     auto_sync.log
REM   para evitar conflictos durante pull/rebase.
REM
REM - Este script está pensado para:
REM     REPO_DIR = C:\Users\thier\Desktop\tubby_app
REM     BRANCH   = main
REM     REMOTE   = origin
REM
REM - Si usas otra ruta o rama, cambia variables en "CONFIGURACIÓN".
REM ================================================================================


REM =========================
REM CONFIGURACIÓN PRINCIPAL
REM =========================
set REPO_DIR=C:\Users\thier\Desktop\tubby_app
set LOG_FILE=%REPO_DIR%\auto_sync.log
set BRANCH=main
set REMOTE=origin


REM =========================================================
REM PASO 0: ENTRAR A LA CARPETA DEL REPOSITORIO
REM =========================================================
cd /d "%REPO_DIR%" || (
  REM Si no puede entrar en la carpeta, termina con error.
  echo [%date% %time%] ERROR: No se pudo acceder a %REPO_DIR%>> "%LOG_FILE%"
  exit /b 1
)

REM Verificar que realmente sea un repositorio Git.
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR: La carpeta no es un repositorio Git valido.>> "%LOG_FILE%"
  exit /b 1
)


REM =========================================================
REM PASO 1: CONSULTAR CAMBIOS REMOTOS (NUBE) SIN MEZCLAR AÚN
REM =========================================================
REM "git fetch" trae referencias remotas pero no modifica tu working tree.
git fetch %REMOTE% %BRANCH% >nul 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR: Fallo en git fetch %REMOTE% %BRANCH%.>> "%LOG_FILE%"
  exit /b 1
)

REM Contar cuántos commits remotos están por delante del local:
REM HEAD..origin/main
set REMOTE_CHANGED=0
set REMOTE_AHEAD=0
for /f %%i in ('git rev-list --count HEAD..%REMOTE%/%BRANCH%') do set REMOTE_AHEAD=%%i
if not "%REMOTE_AHEAD%"=="0" set REMOTE_CHANGED=1


REM =========================================================
REM PASO 2: CONSULTAR CAMBIOS LOCALES (ORDENADOR)
REM =========================================================
REM Stage de cambios para poder detectarlos de forma fiable.
git add -A >nul 2>&1

REM Si hay diferencias en staging, hay cambios locales reales.
set LOCAL_CHANGED=0
git diff --cached --quiet
if errorlevel 1 set LOCAL_CHANGED=1


REM =========================================================
REM PASO 3: SI NO HAY CAMBIOS, SALIR SIN HACER NADA
REM =========================================================
if "%REMOTE_CHANGED%"=="0" if "%LOCAL_CHANGED%"=="0" (
  echo [%date% %time%] Sin cambios locales/remotos. No se realiza ninguna accion.>> "%LOG_FILE%"
  exit /b 0
)

REM Si llegó aquí, hay algo que sincronizar.
echo ==================================================>> "%LOG_FILE%"
echo [%date% %time%] Cambios detectados. Iniciando sincronizacion...>> "%LOG_FILE%"
echo [%date% %time%] Estado detectado: REMOTE_CHANGED=%REMOTE_CHANGED% LOCAL_CHANGED=%LOCAL_CHANGED%>> "%LOG_FILE%"


REM =========================================================
REM PASO 4: SI HAY CAMBIOS REMOTOS, BAJARLOS PRIMERO
REM =========================================================
if "%REMOTE_CHANGED%"=="1" (
  echo [%date% %time%] Ejecutando: git pull --rebase %REMOTE% %BRANCH%>> "%LOG_FILE%"
  git pull --rebase %REMOTE% %BRANCH% >> "%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [%date% %time%] ERROR: Fallo en pull --rebase (posible conflicto).>> "%LOG_FILE%"
    exit /b 1
  )
)


REM =========================================================
REM PASO 5: SI HAY CAMBIOS LOCALES, SUBIRLOS
REM =========================================================
if "%LOCAL_CHANGED%"=="1" (
  REM Mensaje automático de commit con fecha y hora.
  set MSG=auto-sync %date% %time%

  echo [%date% %time%] Ejecutando: git commit -m "!MSG!">> "%LOG_FILE%"
  git commit -m "!MSG!" >> "%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [%date% %time%] ERROR: Fallo en commit.>> "%LOG_FILE%"
    exit /b 1
  )

  echo [%date% %time%] Ejecutando: git push %REMOTE% %BRANCH%>> "%LOG_FILE%"
  git push %REMOTE% %BRANCH% >> "%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [%date% %time%] ERROR: Fallo en push.>> "%LOG_FILE%"
    exit /b 1
  )
)


REM =========================================================
REM PASO 6: FIN CORRECTO
REM =========================================================
echo [%date% %time%] OK: Sincronizacion completada correctamente.>> "%LOG_FILE%"
exit /b 0