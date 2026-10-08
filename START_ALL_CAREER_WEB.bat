@echo off
title All Career React Web (Localhost:5173)

echo ===============================================================
echo              ALL CAREER REACT WEB APPLICATION                 
echo ===============================================================

set "APP_DIR="

:: 1. Check relative to current bat location (if placed in repo root)
if exist "%~dp0all-career-app\package.json" (
    set "APP_DIR=%~dp0all-career-app"
    goto :FOUND
)

:: 2. Check if bat was pasted inside all-career-app itself
if exist "%~dp0package.json" (
    findstr /i "\"name\": \"all-career-app\"" "%~dp0package.json" >nul 2>&1
    if not errorlevel 1 (
        set "APP_DIR=%~dp0"
        goto :FOUND
    )
)

:: 3. Check if bat was pasted in Documents folder
if exist "%~dp0VS_CODE\ALL_CAREER_3\all-career-app\package.json" (
    set "APP_DIR=%~dp0VS_CODE\ALL_CAREER_3\all-career-app"
    goto :FOUND
)

:: 4. Check absolute path on this machine (works from Desktop, Downloads, USB, anywhere!)
if exist "C:\Users\lrage\OneDrive\Documents\VS_CODE\ALL_CAREER_3\all-career-app\package.json" (
    set "APP_DIR=C:\Users\lrage\OneDrive\Documents\VS_CODE\ALL_CAREER_3\all-career-app"
    goto :FOUND
)

:: 5. Check userprofile with OneDrive
if exist "%USERPROFILE%\OneDrive\Documents\VS_CODE\ALL_CAREER_3\all-career-app\package.json" (
    set "APP_DIR=%USERPROFILE%\OneDrive\Documents\VS_CODE\ALL_CAREER_3\all-career-app"
    goto :FOUND
)

:: 6. Check userprofile without OneDrive
if exist "%USERPROFILE%\Documents\VS_CODE\ALL_CAREER_3\all-career-app\package.json" (
    set "APP_DIR=%USERPROFILE%\Documents\VS_CODE\ALL_CAREER_3\all-career-app"
    goto :FOUND
)

:NOT_FOUND
echo [ERROR] Could not find the all-career-app project directory!
echo Please ensure ALL_CAREER_3 exists at:
echo C:\Users\lrage\OneDrive\Documents\VS_CODE\ALL_CAREER_3\all-career-app
echo.
pause
exit /b 1

:FOUND
echo [OK] Found Web App at: %APP_DIR%
echo [OK] Localhost URL: http://localhost:5173/
echo ===============================================================
echo Starting dev server... Your browser will open automatically.
echo (Leave this window open while using the web app)
echo ===============================================================
echo.

cd /d "%APP_DIR%"

:: Open browser automatically with a slight delay so Vite dev server is ready
start "" cmd /c "ping 127.0.0.1 -n 3 >nul & start http://localhost:5173/"

:: Launch Vite Dev Server using npm.cmd (bypasses PowerShell script execution policies)
call npm.cmd run dev

pause
