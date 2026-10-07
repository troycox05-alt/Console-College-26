@echo off
rem Console College in its own window. Double-click to play.
cd /d "%~dp0"
python play.py %*
if errorlevel 1 pause
