@echo off
setlocal EnableExtensions
title Planner RAG Launcher

REM ============================================================
REM Exact launcher for:
REM   ROOT\package.json
REM   ROOT\src\
REM   ROOT\backend\app\main.py
REM
REM This script NEVER installs or modifies dependencies.
REM ============================================================

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"

if /I "%~1"=="backend" goto RUN_BACKEND
if /I "%~1"=="frontend" goto RUN_FRONTEND

echo.
echo ============================================
echo        Planner RAG - One Click Start
echo ============================================
echo Root: %ROOT%
echo.

REM Verify the exact project structure.
if not exist "%ROOT%package.json" (
    echo [ERROR] package.json was not found in the project root.
    echo Put this BAT file beside package.json.
    pause
    exit /b 1
)

if not exist "%ROOT%src\" (
    echo [ERROR] Frontend src folder was not found.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%\app\main.py" (
    echo [ERROR] Backend entry was not found:
    echo %BACKEND_DIR%\app\main.py
    pause
    exit /b 1
)

REM Frontend dependencies must already exist.
if not exist "%ROOT%node_modules\" (
    echo [ERROR] Existing frontend node_modules was not found.
    echo This launcher will NOT install dependencies.
    pause
    exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm.cmd was not found in PATH.
    echo This launcher will NOT install Node.js or npm.
    pause
    exit /b 1
)

REM Select an existing Python environment only.
set "PYTHON_KIND="

if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_KIND=backend_dotvenv"
    goto PYTHON_FOUND
)

if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_KIND=backend_venv"
    goto PYTHON_FOUND
)

if exist "%ROOT%.venv\Scripts\python.exe" (
    set "PYTHON_KIND=root_dotvenv"
    goto PYTHON_FOUND
)

if exist "%ROOT%venv\Scripts\python.exe" (
    set "PYTHON_KIND=root_venv"
    goto PYTHON_FOUND
)

where python.exe >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_KIND=system_python"
    goto PYTHON_FOUND
)

where py.exe >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_KIND=py_launcher"
    goto PYTHON_FOUND
)

echo [ERROR] No existing Python interpreter was found.
echo Checked backend\.venv, backend\venv, root .venv, root venv,
echo python.exe and py.exe.
echo.
echo This launcher will NOT create an environment or install packages.
pause
exit /b 1

:PYTHON_FOUND
echo [INFO] Existing Python source: %PYTHON_KIND%
echo [1/2] Starting backend...
start "Planner Backend" "%ComSpec%" /d /k call "%~f0" backend "%PYTHON_KIND%"

REM Start in sequence without installing or changing anything.
timeout /t 4 /nobreak >nul

echo [2/2] Starting frontend...
start "Planner Frontend" "%ComSpec%" /d /k call "%~f0" frontend

echo.
echo Backend command:
echo   python -m uvicorn app.main:app --reload --port 8000
echo Frontend command:
echo   npm run dev
echo.
echo No dependencies were installed or modified.
echo Close the two service windows to stop the project.
echo.
exit /b 0


:RUN_BACKEND
set "PYTHON_KIND=%~2"
cd /d "%BACKEND_DIR%"

echo.
echo ============================================
echo Planner Backend
echo Directory: %CD%
echo Entry: app.main:app
echo ============================================
echo.

if /I "%PYTHON_KIND%"=="backend_dotvenv" (
    "%BACKEND_DIR%\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
    goto BACKEND_END
)

if /I "%PYTHON_KIND%"=="backend_venv" (
    "%BACKEND_DIR%\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
    goto BACKEND_END
)

if /I "%PYTHON_KIND%"=="root_dotvenv" (
    "%ROOT%.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
    goto BACKEND_END
)

if /I "%PYTHON_KIND%"=="root_venv" (
    "%ROOT%venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
    goto BACKEND_END
)

if /I "%PYTHON_KIND%"=="system_python" (
    python.exe -m uvicorn app.main:app --reload --port 8000
    goto BACKEND_END
)

if /I "%PYTHON_KIND%"=="py_launcher" (
    py.exe -3 -m uvicorn app.main:app --reload --port 8000
    goto BACKEND_END
)

echo [ERROR] Unknown Python source: %PYTHON_KIND%

:BACKEND_END
echo.
echo Backend process exited.
echo No packages were installed by this launcher.
pause
exit /b


:RUN_FRONTEND
cd /d "%ROOT%"

echo.
echo ============================================
echo Planner Frontend
echo Directory: %CD%
echo Command: npm run dev
echo ============================================
echo.

call npm.cmd run dev

echo.
echo Frontend process exited.
echo No packages were installed by this launcher.
pause
exit /b
