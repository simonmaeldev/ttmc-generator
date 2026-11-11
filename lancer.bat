@echo off
cd /d "%~dp0"
set PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%
uv run python app.py
pause
