@echo off
REM Copyright (C) 2026 Abdul Moez (https://github.com/Abdul-Moez)
REM SPDX-License-Identifier: GPL-3.0-or-later -- see the LICENSE file.
REM
REM Builds the installable app, from start to finish:
REM
REM   dist\CrystalX Nova X21\CrystalXNova.exe      the app, with its own Python
REM   dist\CrystalX-Nova-X21-Setup-<version>.exe   the installer for it
REM
REM   packaging\build.cmd                              uses the Python it finds
REM   packaging\build.cmd "C:\path\to\python.exe"      uses that one
REM
REM The build tools go into folders of this project that are not part of the
REM source (venv-build, downloads, inno); nothing is installed on the PC. The
REM first run needs the internet for them. Safe to run again.
setlocal
cd /d "%~dp0.."

REM Inno Setup makes the installer. It is downloaded once, never stored with
REM the source, and checked against this fingerprint and its digital signature
REM before it is used. Change the two together.
set "INNO_URL=https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe"
set "INNO_SHA256=0362A383ED217D4C4239B5933866DD96D3EB2102737DA92F80F6057A4B40DF2F"

if exist "venv-build\Scripts\python.exe" goto tools

REM Exit code 0 = usable, 2 = older than 3.10, 3 = exactly 3.13.0, which is
REM refused: in an environment made by it the window toolkit (tkinter) cannot
REM start, so the settings window would be missing from the app.
set "CHECK=import sys, tkinter; v = sys.version_info[:3]; sys.exit(3 if v == (3, 13, 0) else 0 if v >= (3, 10) else 2)"
set "PY="
if "%~1"=="" goto search
"%~1" -c "%CHECK%" >nul 2>&1
if errorlevel 1 goto badpython
set PY="%~1"
goto makevenv

:search
REM Prefer the "py" launcher that the python.org installer adds; fall back to
REM "python". The check also rules out the Microsoft Store placeholder.
py -3 -c "%CHECK%" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "%CHECK%" >nul 2>&1 && set "PY=python"
if defined PY goto makevenv

:badpython
echo.
echo No usable Python was found. It must be 3.10 or newer, but not 3.13.0
echo (that one version has a bug that breaks the build), and have tkinter.
echo Install the latest from https://www.python.org/downloads/windows/ -- or,
echo if you have a good one that is not the default, give its path:
echo     packaging\build.cmd "C:\path\to\python.exe"
goto failed

:makevenv
echo Creating venv-build ...
%PY% -m venv venv-build || goto failed

:tools
"venv-build\Scripts\python.exe" -c "import tkinter; tkinter.Tcl()" >nul 2>&1
if errorlevel 1 (
    echo.
    echo The Python in the venv-build folder cannot start tkinter, so the app
    echo would be built without its settings window. Delete the venv-build
    echo folder and run this again with a good Python.
    goto failed
)
echo Installing the build tools ...
"venv-build\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r packaging\requirements-build.txt || goto failed

echo Building the app ...
"venv-build\Scripts\pyinstaller.exe" packaging\crystalx-nova.spec --noconfirm --log-level WARN || goto failed

if exist "inno\ISCC.exe" goto installer
echo Downloading Inno Setup ...
if not exist downloads mkdir downloads
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop'; $out = 'downloads\innosetup.exe';" ^
  "Invoke-WebRequest -Uri $env:INNO_URL -OutFile $out;" ^
  "$hash = (Get-FileHash $out -Algorithm SHA256).Hash;" ^
  "if ($hash -ne $env:INNO_SHA256) { throw \"SHA-256 is $hash, expected $env:INNO_SHA256\" };" ^
  "$signature = Get-AuthenticodeSignature $out;" ^
  "if ($signature.Status -ne 'Valid') { throw \"signature is $($signature.Status)\" };" ^
  "Write-Host ('  checksum and signature OK: ' + $signature.SignerCertificate.Subject);" ^
  "Start-Process $out -Wait -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/PORTABLE=1',('/DIR=\"' + (Join-Path (Get-Location) 'inno') + '\"')" || goto failed
if not exist "inno\ISCC.exe" goto failed

:installer
set "VERSION="
for /f %%v in ('venv-build\Scripts\python.exe -c "import mouse_win; print(mouse_win.VERSION)"') do set "VERSION=%%v"
if not defined VERSION (
    echo Could not read the version from mouse_win.py.
    goto failed
)
echo Building the installer for version %VERSION% ...
"inno\ISCC.exe" /Q "/DAppVersion=%VERSION%" packaging\installer.iss || goto failed

echo.
echo Done:
echo   dist\CrystalX Nova X21\CrystalXNova.exe
echo   dist\CrystalX-Nova-X21-Setup-%VERSION%.exe
exit /b 0

:failed
echo.
echo The build failed -- see the messages above.
exit /b 1
