@echo off
title ALL CAREER Scraper - DEBUG MODE (Terminal Visible)
echo ============================================================
echo   ALL CAREER SCRAPER - DEBUG MODE
echo   You can see all scraping activity here.
echo   Close this window to stop.
echo ============================================================
echo.
cd /d "%~dp0"
python local_scraper.py
pause
