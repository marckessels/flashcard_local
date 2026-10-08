@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Maak eerst een virtuele omgeving en installeer requirements.txt. Zie README.md.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m streamlit run app.py
pause
