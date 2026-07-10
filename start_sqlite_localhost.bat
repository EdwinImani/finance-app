@echo off
cd /d "%~dp0"
set DATABASE_URL=sqlite:///local_db.sqlite3
echo Starting finance-app from: %CD%
echo DATABASE_URL=%DATABASE_URL%
echo Open: http://127.0.0.1:8000/__server_check__/
C:\Python314\python.exe manage.py runserver 127.0.0.1:8000 --noreload
pause
