#!/usr/bin/env python3
# CrystalX Nova X21 mouse for Windows
# Copyright (C) 2026 Abdul Moez (https://github.com/Abdul-Moez)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program (the LICENSE file). If not, see
# <https://www.gnu.org/licenses/>.
#
# Additional term under section 7(b) of the GNU GPL version 3: the author
# attribution "Abdul Moez (https://github.com/Abdul-Moez)" must be preserved
# in this file and in all copies and modified versions of it.
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Nova X21's battery, as an icon near the clock.

The mouse needs none of this: it keeps its own settings and works the same
with the icon running or not. The icon is only a way to see the battery
without picking the mouse up, and a way into the settings window.

It is built to cost nothing while it sits there. The mouse reports its
battery by itself every two seconds while it lies still, and one thread
sleeps inside Windows until a report comes. Only when none has come for 20
seconds is the mouse asked one question, to tell a sleeping mouse from one
that is being moved (see mouse_win.awake); a mouse found asleep is not asked
again. The icon is redrawn only when the number on it changes. No timer
runs, the settings window is a separate program that exists only while it
is open, and nothing here loads tkinter or any library outside Python
itself.

Usage:
    tray_win.py             show the icon and open the settings window
    tray_win.py --hidden    show the icon only (used at login)
"""

import ctypes
import os
import sys
import threading
from ctypes import wintypes as wt

import mouse_win
from mouse_win import DISPLAY_NAME

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW_SCRIPT = os.path.join(HERE, "window_win.py")
TRAY_CLASS = "CrystalXNovaTray"
MUTEX = "Local\\CrystalXNovaTray"
# The settings window: what Tk calls its windows, and the title it is given.
WINDOW_CLASS = "TkTopLevel"

WM_DESTROY, WM_CLOSE, WM_COMMAND, WM_NULL = 0x0002, 0x0010, 0x0111, 0x0000
WM_DEVICECHANGE, DBT_DEVNODES_CHANGED = 0x0219, 0x0007
WM_LBUTTONUP, WM_LBUTTONDBLCLK, WM_RBUTTONUP = 0x0202, 0x0203, 0x0205
WM_APP = 0x8000
WM_TRAY = WM_APP + 1        # the icon was clicked
WM_STATUS = WM_APP + 2      # the watching thread has news
WM_SHOW_APP = WM_APP + 3    # a second launch asks for the window
ID_SHOW, ID_QUIT = 1, 2
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4

AWAKE, ASLEEP, ABSENT = 0, 1, 2
UNKNOWN = 0xFF              # no battery reading yet

GREEN, AMBER, RED = (46, 158, 79), (214, 140, 0), (208, 52, 52)
BLUE, GREY = (36, 118, 214), (112, 112, 112)

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT),
                ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT),
                ("hIcon", wt.HICON), ("szTip", wt.WCHAR * 128),
                ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
                ("szInfo", wt.WCHAR * 256), ("uVersion", wt.UINT),
                ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wt.HICON)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
                ("hbmMask", wt.HBITMAP), ("hbmColor", wt.HBITMAP)]


def _api(function, result, *arguments):
    function.restype, function.argtypes = result, arguments


_api(user32.DefWindowProcW, LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
_api(user32.RegisterClassW, wt.ATOM, ctypes.POINTER(WNDCLASS))
_api(user32.CreateWindowExW, wt.HWND, wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU,
     wt.HINSTANCE, wt.LPVOID)
_api(user32.GetMessageW, wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT)
_api(user32.DispatchMessageW, LRESULT, ctypes.POINTER(wt.MSG))
_api(user32.PostMessageW, wt.BOOL, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
_api(user32.PostQuitMessage, None, ctypes.c_int)
_api(user32.DestroyWindow, wt.BOOL, wt.HWND)
_api(user32.RegisterWindowMessageW, wt.UINT, wt.LPCWSTR)
_api(user32.FindWindowW, wt.HWND, wt.LPCWSTR, wt.LPCWSTR)
_api(user32.SetForegroundWindow, wt.BOOL, wt.HWND)
_api(user32.GetCursorPos, wt.BOOL, ctypes.POINTER(wt.POINT))
_api(user32.CreatePopupMenu, wt.HMENU)
_api(user32.AppendMenuW, wt.BOOL, wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR)
_api(user32.TrackPopupMenu, wt.BOOL, wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
     ctypes.c_int, wt.HWND, ctypes.c_void_p)
_api(user32.DestroyMenu, wt.BOOL, wt.HMENU)
_api(user32.GetSystemMetrics, ctypes.c_int, ctypes.c_int)
_api(user32.DrawTextW, ctypes.c_int, wt.HDC, wt.LPCWSTR, ctypes.c_int,
     ctypes.POINTER(wt.RECT), wt.UINT)
_api(user32.CreateIconIndirect, wt.HICON, ctypes.POINTER(ICONINFO))
_api(user32.DestroyIcon, wt.BOOL, wt.HICON)
_api(shell32.Shell_NotifyIconW, wt.BOOL, wt.DWORD, ctypes.POINTER(NOTIFYICONDATA))
_api(shell32.ShellExecuteW, wt.HINSTANCE, wt.HWND, wt.LPCWSTR, wt.LPCWSTR,
     wt.LPCWSTR, wt.LPCWSTR, ctypes.c_int)
_api(gdi32.CreateCompatibleDC, wt.HDC, wt.HDC)
_api(gdi32.CreateDIBSection, wt.HBITMAP, wt.HDC, ctypes.POINTER(BITMAPINFOHEADER),
     wt.UINT, ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD)
_api(gdi32.CreateBitmap, wt.HBITMAP, ctypes.c_int, ctypes.c_int, wt.UINT, wt.UINT,
     ctypes.c_void_p)
_api(gdi32.CreateFontW, wt.HFONT, *[ctypes.c_int] * 5, *[wt.DWORD] * 8, wt.LPCWSTR)
_api(gdi32.SelectObject, wt.HGDIOBJ, wt.HDC, wt.HGDIOBJ)
_api(gdi32.SetBkMode, ctypes.c_int, wt.HDC, ctypes.c_int)
_api(gdi32.SetTextColor, wt.COLORREF, wt.HDC, wt.COLORREF)
_api(gdi32.DeleteObject, wt.BOOL, wt.HGDIOBJ)
_api(gdi32.DeleteDC, wt.BOOL, wt.HDC)
_api(gdi32.GdiFlush, wt.BOOL)
_api(kernel32.CreateMutexW, wt.HANDLE, ctypes.c_void_p, wt.BOOL, wt.LPCWSTR)
_api(kernel32.GetModuleHandleW, wt.HMODULE, wt.LPCWSTR)


# -- the icon -----------------------------------------------------------------

def _canvas(dc, size):
    """A size x size bitmap, 4 bytes a pixel, and where its pixels are."""
    header = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=size,
                              biHeight=-size, biPlanes=1, biBitCount=32)
    bits = ctypes.c_void_p()
    return gdi32.CreateDIBSection(dc, ctypes.byref(header), 0,
                                  ctypes.byref(bits), None, 0), bits


def icon_pixels(text, colour, size):
    """The icon as BGRA bytes: `text` in white on a rounded square of `colour`.

    Windows draws the text, white on black, and how white each pixel came
    out says how much of the letter covers it. The square is laid under it
    here, because text drawn by Windows carries no transparency of its own.
    """
    dc = gdi32.CreateCompatibleDC(None)
    bitmap, bits = _canvas(dc, size)
    old_bitmap = gdi32.SelectObject(dc, bitmap)
    # Two digits fill the square; "100" needs smaller ones to fit.
    height = round(size * (0.80 if len(text) < 3 else 0.54))
    font = gdi32.CreateFontW(-height, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0,
                             4, 0, "Segoe UI")       # 4: smooth, not ClearType
    old_font = gdi32.SelectObject(dc, font)
    gdi32.SetBkMode(dc, 1)
    gdi32.SetTextColor(dc, 0xFFFFFF)
    box = wt.RECT(0, -round(size * 0.06), size, size)
    user32.DrawTextW(dc, text, -1, ctypes.byref(box), 0x25)  # centred, one line
    gdi32.GdiFlush()
    drawn = ctypes.string_at(bits, size * size * 4)
    gdi32.SelectObject(dc, old_font)
    gdi32.SelectObject(dc, old_bitmap)
    gdi32.DeleteObject(font)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(dc)

    red, green, blue = colour
    radius = size / 5
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            # Inside the square, unless in a corner beyond its rounding.
            cx = min(max(x + 0.5, radius), size - radius)
            cy = min(max(y + 0.5, radius), size - radius)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 > radius * radius:
                continue
            i = (y * size + x) * 4
            cover = drawn[i + 1]
            out[i] = blue + (255 - blue) * cover // 255
            out[i + 1] = green + (255 - green) * cover // 255
            out[i + 2] = red + (255 - red) * cover // 255
            out[i + 3] = 255
    return bytes(out)


def make_icon(text, colour):
    size = user32.GetSystemMetrics(49)      # the size of a small icon
    pixels = icon_pixels(text, colour, size)
    dc = gdi32.CreateCompatibleDC(None)
    colour_bitmap, bits = _canvas(dc, size)
    ctypes.memmove(bits, pixels, len(pixels))
    # The mask marks the see-through pixels, for whatever ignores the alpha.
    stride = (size + 15) // 16 * 2
    mask = bytearray(stride * size)
    for y in range(size):
        for x in range(size):
            if not pixels[(y * size + x) * 4 + 3]:
                mask[y * stride + x // 8] |= 0x80 >> x % 8
    mask_bitmap = gdi32.CreateBitmap(size, size, 1, 1, bytes(mask))
    info = ICONINFO(True, 0, 0, mask_bitmap, colour_bitmap)
    icon = user32.CreateIconIndirect(ctypes.byref(info))
    gdi32.DeleteObject(mask_bitmap)
    gdi32.DeleteObject(colour_bitmap)
    gdi32.DeleteDC(dc)
    return icon


def look(state, battery, charging):
    """(text on the icon, its colour, the tooltip) for what is known."""
    known = battery != UNKNOWN
    number = str(battery) if known else "?"
    if state == ABSENT:
        return "-", GREY, f"{DISPLAY_NAME} - receiver not plugged in"
    if state == ASLEEP:
        was = f" (battery was {battery}%)" if known else ""
        return number, GREY, f"{DISPLAY_NAME} - asleep or switched off{was}"
    if not known:
        return number, GREY, f"{DISPLAY_NAME} - waiting for the mouse"
    if charging:
        return number, BLUE, f"{DISPLAY_NAME} - battery {battery}%, charging"
    colour = GREEN if battery >= 50 else AMBER if battery >= 20 else RED
    return number, colour, f"{DISPLAY_NAME} - battery {battery}%"


# -- the app ------------------------------------------------------------------

def show_window():
    """Open the settings window. It is a program of its own, so that none of
    it stays in memory once it is closed; a copy already open comes to the
    front instead (it sees to that itself)."""
    if getattr(sys, "frozen", False):
        program, arguments = sys.executable, "--window"
    else:
        program, arguments = sys.executable, f'"{WINDOW_SCRIPT}"'
    shell32.ShellExecuteW(None, "open", program, arguments, HERE, 1)


class Tray:
    def __init__(self):
        self.state, self.battery, self.charging = ABSENT, UNKNOWN, False
        self.shown = None           # what the icon shows now (see look)
        self.icon = None
        self.quitting = False
        self.listener = None
        self.plugged = threading.Event()    # something was plugged in or out
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")
        self.proc = WNDPROC(self.handle)    # kept: Windows calls it for good
        cls = WNDCLASS(lpfnWndProc=self.proc, lpszClassName=TRAY_CLASS,
                       hInstance=kernel32.GetModuleHandleW(None))
        user32.RegisterClassW(ctypes.byref(cls))
        # Never shown. It is a real window, not a message-only one, because
        # only real windows are told when a device is plugged in.
        self.hwnd = user32.CreateWindowExW(0, TRAY_CLASS, "", 0, 0, 0, 0, 0,
                                           None, None, cls.hInstance, None)

    # Called by Windows, on the main thread.
    def handle(self, hwnd, message, wparam, lparam):
        if message == WM_TRAY:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                show_window()
            elif lparam == WM_RBUTTONUP:
                self.menu()
        elif message == WM_STATUS:
            self.state, self.battery = wparam, lparam & 0xFF
            self.charging = bool(lparam >> 8)
            self.refresh()
        elif message == WM_SHOW_APP:
            show_window()
        elif message == WM_COMMAND:
            if wparam & 0xFFFF == ID_SHOW:
                show_window()
            elif wparam & 0xFFFF == ID_QUIT:
                self.quit()
        elif message == WM_DEVICECHANGE and wparam == DBT_DEVNODES_CHANGED:
            self.plugged.set()
        elif message == self.taskbar_created:
            # Explorer restarted and forgot every icon.
            self.shown = None
            self.refresh(add=True)
        elif message == WM_DESTROY:
            user32.PostQuitMessage(0)
        else:
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)
        return 0

    def refresh(self, add=False):
        """Bring the icon up to date; a no-op unless what it shows changed."""
        want = look(self.state, self.battery, self.charging)
        if want == self.shown:
            return
        data = NOTIFYICONDATA(cbSize=ctypes.sizeof(NOTIFYICONDATA), hWnd=self.hwnd,
                              uID=1, uFlags=NIF_MESSAGE | NIF_ICON | NIF_TIP,
                              uCallbackMessage=WM_TRAY, szTip=want[2][:127])
        old = self.icon
        if self.shown is None or want[:2] != self.shown[:2]:
            self.icon = make_icon(want[0], want[1])
        data.hIcon = self.icon
        if not shell32.Shell_NotifyIconW(NIM_ADD if add or self.shown is None
                                         else NIM_MODIFY, ctypes.byref(data)):
            shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data))
        if old and old != self.icon:
            user32.DestroyIcon(old)
        self.shown = want

    def menu(self):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, 0x1, 0, self.shown[2].split(" - ", 1)[1].capitalize())
        user32.AppendMenuW(menu, 0x800, 0, None)
        user32.AppendMenuW(menu, 0, ID_SHOW, "Show")
        user32.AppendMenuW(menu, 0, ID_QUIT, "Quit")
        point = wt.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        # Without these two the menu stays up when clicking elsewhere.
        user32.SetForegroundWindow(self.hwnd)
        user32.TrackPopupMenu(menu, 0x2, point.x, point.y, 0, self.hwnd, None)
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)

    # The watching thread. It never touches the icon: it posts what it
    # learned to the window, and the main thread acts on it.
    def watch(self):
        recent = []
        while not self.quitting:
            try:
                self.listener = mouse_win.Listener()
            except mouse_win.MouseError:
                self.post(ABSENT)
                # Sleeps here until Windows says a device came or went. A
                # receiver shows up in several steps, so look a few times.
                self.plugged.wait()
                self.plugged.clear()
                for _ in range(4):
                    if self.quitting or mouse_win.locate():
                        break
                    self.plugged.wait(1)
                continue
            # The receiver is there. Until the mouse speaks, that is all that
            # is known (a mouse in use can stay quiet for a good while).
            self.post(AWAKE)
            try:
                asleep = False
                while True:
                    status = self.listener.wait()
                    if status is None:
                        # Quiet for a while. That is a sleeping mouse, or one
                        # being moved: it only reports while it lies still.
                        # One question settles it, and once it is known to
                        # sleep nothing more is asked until it speaks again.
                        if not asleep and mouse_win.awake() is False:
                            asleep = True
                            self.post(ASLEEP)
                        continue
                    asleep = False
                    # The reading wavers by a point or two; show the middle
                    # of the last few, so the icon is not redrawn for that.
                    recent = (recent + [status.battery])[-5:]
                    self.battery = sorted(recent)[len(recent) // 2]
                    self.charging = status.charging
                    self.post(AWAKE)
            except mouse_win.MouseError:
                pass
            finally:
                self.listener.close()
                self.listener = None
        user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def post(self, state):
        user32.PostMessageW(self.hwnd, WM_STATUS, state,
                            self.battery | self.charging << 8)

    def quit(self):
        """Take the icon away and end; the settings window goes too."""
        self.quitting = True
        window = user32.FindWindowW(WINDOW_CLASS, DISPLAY_NAME)
        if window:
            user32.PostMessageW(window, WM_CLOSE, 0, 0)
        data = NOTIFYICONDATA(cbSize=ctypes.sizeof(NOTIFYICONDATA),
                              hWnd=self.hwnd, uID=1)
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
        if self.listener:
            self.listener.stop()
        self.plugged.set()
        user32.DestroyWindow(self.hwnd)

    def run(self, show):
        self.refresh(add=True)
        threading.Thread(target=self.watch, name="mouse", daemon=True).start()
        if show:
            show_window()
        message = wt.MSG()
        # Blocks inside Windows until there is something to do.
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.DispatchMessageW(ctypes.byref(message))
        if self.icon:
            user32.DestroyIcon(self.icon)


def main():
    if "--window" in sys.argv[1:]:
        # Not the icon but the settings window: the same program, started
        # with this option once it is packaged as one .exe.
        import window_win
        window_win.main()
        return
    hidden = "--hidden" in sys.argv[1:]
    # One icon per user session. A second launch -- say from the Start menu --
    # asks the running one to show the window, then exits.
    mutex = kernel32.CreateMutexW(None, False, MUTEX)
    if ctypes.get_last_error() == 183:      # ERROR_ALREADY_EXISTS
        running = user32.FindWindowW(TRAY_CLASS, None)
        if running and not hidden:
            user32.PostMessageW(running, WM_SHOW_APP, 0, 0)
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # a crisp icon on high-DPI screens
    except (AttributeError, OSError):
        pass
    Tray().run(show=not hidden)
    del mutex


if __name__ == "__main__":
    main()
