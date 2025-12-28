@echo off
REM Build script for Windows executable
REM Run this from the project root directory

echo Installing dependencies...
pip install -e .[dev]

echo.
echo Building executable...
pyinstaller tts_chatterbox.spec

echo.
echo Build complete!
echo Executable is located at: dist\tts_chatterbox\tts_chatterbox.exe
pause
