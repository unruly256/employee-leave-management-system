@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Create it with: py -m venv .venv
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python manage.py check
if errorlevel 1 pause & exit /b 1
python manage.py migrate
if errorlevel 1 pause & exit /b 1
python manage.py runserver
pause
