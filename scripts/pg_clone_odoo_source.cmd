@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pg_clone_odoo_source.ps1" %*
endlocal
