@echo off
setlocal

:: Get the directory of the script
set "SCRIPT_DIR=%~dp0"

:: Change to the script directory
cd /d "%SCRIPT_DIR%"

:: Activate the virtual environment
call .\env\Scripts\activate

:: Run the Python script with all passed arguments
python main.py %*