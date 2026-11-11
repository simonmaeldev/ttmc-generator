@echo off
echo === Installation TTMC Generator ===

where uv >nul 2>&1
if errorlevel 1 (
    echo Installation de uv...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%
)

echo Installation des dependances Python...
uv sync

echo.
echo Installation terminee. Double-clique sur lancer.bat pour demarrer.
pause
