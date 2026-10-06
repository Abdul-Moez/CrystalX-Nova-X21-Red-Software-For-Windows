# -*- mode: python -*-
# CrystalX Nova X21 mouse for Windows
# Copyright (C) 2026 Abdul Moez (https://github.com/Abdul-Moez)
# SPDX-License-Identifier: GPL-3.0-or-later -- see the LICENSE file.
#
# PyInstaller recipe for the installable app: one program, CrystalXNova.exe,
# with its own bundled Python.
#
#   CrystalXNova.exe             the battery icon, and it opens the window
#   CrystalXNova.exe --hidden    the battery icon only (used at login)
#   CrystalXNova.exe --window    the settings window (the icon starts this)
#
# Build from the project folder (or just run packaging\build.cmd):
#   pip install -r packaging\requirements-build.txt
#   pyinstaller packaging\crystalx-nova.spec --noconfirm
import os
import re

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo,
    VarStruct, VSVersionInfo)

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
ICON = os.path.join(ROOT, "assets", "crystalx-nova.ico")
with open(os.path.join(ROOT, "mouse_win.py"), encoding="utf-8") as f:
    VERSION = re.search(r'^VERSION = "([\d.]+)"', f.read(), re.M).group(1)


def version_info(description, filename):
    """The file properties Windows shows -- and the name Task Manager lists
    the process under, instead of a blank or "python"."""
    numbers = tuple(int(n) for n in VERSION.split(".")) + (0,) * (4 - len(VERSION.split(".")))
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "Abdul Moez"),
                StringStruct("FileDescription", description),
                StringStruct("FileVersion", VERSION),
                StringStruct("InternalName", filename),
                StringStruct("LegalCopyright",
                             "Copyright (C) 2026 Abdul Moez. GPL-3.0-or-later."),
                StringStruct("OriginalFilename", filename),
                StringStruct("ProductName", "CrystalX Nova X21"),
                StringStruct("ProductVersion", VERSION),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ])


app = Analysis(
    [os.path.join(ROOT, "tray_win.py")],
    pathex=[ROOT],
    datas=[(ICON, "assets"), (os.path.join(ROOT, "LICENSE"), ".")],
    # The window is imported only when asked for (--window), inside a
    # function; name it so that it and tkinter are sure to be packed.
    hiddenimports=["window_win"],
)
exe = EXE(
    PYZ(app.pure), app.scripts, [],
    exclude_binaries=True,
    name="CrystalXNova",
    icon=ICON,
    version=version_info("CrystalX Nova X21", "CrystalXNova.exe"),
    console=False,
    upx=False,              # packed executables upset antivirus scanners
)
COLLECT(
    exe, app.binaries, app.datas,
    name="CrystalX Nova X21",
    upx=False,
)
