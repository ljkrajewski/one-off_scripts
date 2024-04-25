@echo off

rem Batch wrapper for PowerShell script (bypasses execution policy)
rem To use, rename this file to the name of the PS script you want to run, changing ".ps1" to ".bat".
rem (e.g., "my-script.bat" will run "my-script.ps1")
rem https://www.howtogeek.com/204088/how-to-use-a-batch-file-to-make-powershell-scripts-easier-to-run/

echo "'%~dpn0.ps1' '%*'"
PowerShell.exe -NoProfile -ExecutionPolicy Bypass -Command "& '%~dpn0.ps1' '%*'"
PAUSE
