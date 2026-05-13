@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pg_link_odoo_core.ps1" %*
endlocal
