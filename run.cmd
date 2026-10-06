@echo off
REM Copyright (C) 2026 Abdul Moez (https://github.com/Abdul-Moez)
REM SPDX-License-Identifier: GPL-3.0-or-later -- see the LICENSE file.
REM
REM Shows the Nova X21's battery icon near the clock and opens the settings
REM window. Nothing is installed, and no admin rights are asked for. The
REM mouse keeps its own settings: choose Quit on the icon whenever you like,
REM and the mouse carries on the same.
cd /d "%~dp0"

REM Any Python from 3.10 on, with the tkinter that the python.org installer
REM includes. The check also rules out the Microsoft Store placeholder, which
REM exists on every Windows install but is not a real Python.
set "CHECK=import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 2)"

REM Prefer the "py" launcher that the python.org installer adds; fall back to
REM "python". What is started is the windowless twin, which opens no console.
set "PYW="
py -3 -c "%CHECK%" >nul 2>&1 && set "PYW=pyw -3"
if not defined PYW python -c "%CHECK%" >nul 2>&1 && set "PYW=pythonw"
if defined PYW goto run
echo.
echo Python 3.10 or newer was not found.
echo Install it from https://www.python.org/downloads/windows/ and tick
echo "Add python.exe to PATH" during the install, then run this again.
echo.
pause
exit /b 1

:run
start "" %PYW% tray_win.py %*
