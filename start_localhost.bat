@echo off
cd /d "%~dp0"
set DB_PASSWORD=Nima1357@
python manage.py runserver 127.0.0.1:8000
