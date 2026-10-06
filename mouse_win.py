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
"""Read and change the settings of a CrystalX Nova X21 mouse, from Windows.

The mouse talks to the PC through its 2.4 GHz receiver (or its cable), which
shows up as several HID devices. One of them, usage page FF05, carries the
settings: every request is a 9-byte feature report, [report id, command,
arguments...]. A read command has its top bit set, and its answer is read
back as a feature report that repeats the command; the same command with the
top bit clear writes the value. The mouse keeps what it is sent -- there is
no separate "save".

A macro is the one thing too big for that: it is 320 bytes, moved in ten
pieces of 32 (see `Mouse.read_macro` and `macro_bytes`).

On the same device the mouse also reports by itself, every few seconds while
it is awake: battery, DPI stage, report rate (see `Status`). Nothing has to
ask for those.

Windows' own HID driver does all of it, so this needs no driver, no extra
library and no admin rights.

Close the vendor's NOVA X21 Red app first: it asks the mouse the same
questions on a timer, and two programs asking at once read each other's
answers.

Usage:
    mouse_win.py                    print every setting and the battery
    mouse_win.py --find             only locate the mouse; send nothing
    mouse_win.py --watch            print what the mouse reports, as it comes
    mouse_win.py --export FILE      save every setting to a profile file
    mouse_win.py --import FILE      send a profile file to the mouse
    mouse_win.py --set debounce=10  change settings (rate, lod, sensor_mode,
                                    ripple, angle_snap, motion_sync, debounce,
                                    sleep, stages, stage, fire_times,
                                    fire_speed, dpi1..6)
"""

import ctypes
import struct
import sys
import threading
import time
from ctypes import wintypes as wt

VERSION = "1.0.0"
DISPLAY_NAME = "CrystalX Nova X21"

# The receiver, and the same mouse on its cable.
DEVICES = {(0x093A, 0x522C): "2.4G receiver", (0x093A, 0x622C): "cable"}
USAGE_PAGE = 0xFF05

# Read commands; clear the top bit for the one that writes.
GET_KEY = 0x86          # + key, 0 to 5
GET_MACRO = 0x87        # + pieces, piece, bytes in a piece, key
GET_OPTION = 0x89       # + 1 debounce, 2 fire key, 3 sleep time
GET_SENSOR = 0x8A       # + 1 LOD, 2 ripple, 3 angle snap, 4 motion sync, 5 mode
GET_DPI_SETUP = 0x8B
GET_DPI_STAGE = 0x8C    # + stage, 0 to 5
GET_REPORT_RATE = 0x8D
GET_STATUS = 0x8F
WRITE = 0x7F            # get & WRITE = set

LOD, RIPPLE, ANGLE_SNAP, MOTION_SYNC, SENSOR_MODE = 1, 2, 3, 4, 5
DEBOUNCE, FIRE_OPTION, SLEEP = 1, 2, 3

# How long the vendor app waits between asking and reading the answer, and
# how long this waits after a write before reading the value back.
REPLY_WAIT = 0.010
STATUS_WAIT = 0.030
WRITE_WAIT = 0.100

# Report rate in Hz -> the mouse's code for it.
RATES = {125: 3, 250: 2, 500: 1, 1000: 0, 2000: 6, 4000: 5, 8000: 4}
# For these the mouse's code is the position in the list.
LODS = ("1 mm", "2 mm", "0.7 mm")
SENSOR_MODES = ("Low power", "High performance", "Corded")
# Above this rate the mouse picks the sensor mode itself.
SENSOR_MODE_MAX_RATE = 1000
SLEEP_TIMES = (10, 20, 30) + tuple(range(60, 901, 60))
DEBOUNCE_MAX = 30
FIRE_TIMES_MAX, FIRE_SPEED_MAX = 3, 255
DPI_MIN, DPI_MAX, DPI_STEP = 50, 26000, 50
STAGES = 6

KEYS = ("Left button", "Right button", "Wheel click", "Back (side)",
        "Forward (side)", "DPI button")
# The first five can be given something else to do. The vendor app never
# sets the DPI button or stores a macro for it, so neither does this.
ASSIGNABLE = 5

# What a key does is four bytes, here as one little-endian number: the first
# byte is the kind (1 mouse button, 0 keyboard, 3 media key, 7 DPI, 9 macro,
# 10 fire).
LEFT_CLICK = 0x00F00001
DISABLED = 0
FIRE = 0x0218F00A
MACRO_KIND = 9
FUNCTIONS = (
    ("Left click", LEFT_CLICK),
    ("Right click", 0x00F10001),
    ("Middle click", 0x00F20001),
    ("Back", 0x00F30001),
    ("Forward", 0x00F40001),
    ("Fire (fast clicks)", FIRE),
    ("DPI loop", 0x00030007),
    ("DPI up", 0x00010007),
    ("DPI down", 0x00020007),
    ("Disabled", DISABLED),
    ("Play / Pause", 0x00CD0003),
    ("Next track", 0x00B50003),
    ("Previous track", 0x00B60003),
    ("Stop", 0x00B70003),
    ("Mute", 0x00E20003),
    ("Volume up", 0x00E90003),
    ("Volume down", 0x00EA0003),
    ("Media player", 0x01830003),
    ("Email", 0x018A0003),
    ("Calculator", 0x01920003),
    ("File Explorer", 0x01940003),
    ("Browser: search", 0x02210003),
    ("Browser: home", 0x02230003),
    ("Browser: back", 0x02240003),
    ("Browser: forward", 0x02250003),
    ("Browser: stop", 0x02260003),
    ("Browser: refresh", 0x02270003),
    ("Browser: favorites", 0x022A0003),
)
FUNCTION_NAMES = {value: name for name, value in FUNCTIONS}

# A keyboard shortcut is [0, modifiers, key, second key]; these are the
# modifier bits and the key codes a USB keyboard uses.
MODIFIERS = (("Ctrl", 1), ("Shift", 2), ("Alt", 4), ("Win", 8))
KEY_CODES = {
    **{chr(ord("A") + i): 0x04 + i for i in range(26)},
    **{str(i): 0x1D + i for i in range(1, 10)}, "0": 0x27,
    "Enter": 0x28, "Esc": 0x29, "Backspace": 0x2A, "Tab": 0x2B, "Space": 0x2C,
    "-": 0x2D, "=": 0x2E, "[": 0x2F, "]": 0x30, "\\": 0x31, ";": 0x33,
    "'": 0x34, "`": 0x35, ",": 0x36, ".": 0x37, "/": 0x38,
    **{f"F{i}": 0x39 + i for i in range(1, 13)},
    "Print Screen": 0x46, "Insert": 0x49, "Home": 0x4A, "Page Up": 0x4B,
    "Delete": 0x4C, "End": 0x4D, "Page Down": 0x4E, "Right": 0x4F,
    "Left": 0x50, "Down": 0x51, "Up": 0x52,
}
KEY_NAMES = {code: name for name, code in KEY_CODES.items()}

# A macro can press everything a shortcut can, the four modifier keys as
# keys of their own, and the three main mouse buttons.
MACRO_KEYS = {**KEY_CODES, "Ctrl": 0xE0, "Shift": 0xE1, "Alt": 0xE2, "Win": 0xE3,
              "Left click": 0xF0, "Right click": 0xF1, "Middle click": 0xF2}
MACRO_KEY_NAMES = {code: name for name, code in MACRO_KEYS.items()}
# How a macro repeats; the mouse's code is the position in the list.
MACRO_MODES = ("while held", "until pressed again", "times")
MACRO_HELD, MACRO_TOGGLE, MACRO_TIMES = 0, 1, 2
MACRO_BYTES, MACRO_PIECE, MACRO_PIECES = 320, 32, 10
MACRO_NAME, MACRO_TRAILER = 0x120, 0x130
# The mouse has room for 71 key steps; a wait rides along with the step
# before it, so waits cost nothing.
MACRO_MAX_KEYS = 70
MACRO_MAX_WAIT = 0xFFFF
MACRO_MAX_COUNT = 0xFFFD

# As the mouse comes. `dpi_light` and `dpi_extra` are three bytes of the DPI
# setup that this mouse has no use for (it has no DPI light); they are read
# and sent back unchanged. `macros` holds one per key, or None.
DEFAULTS = {
    "rate": 1000, "lod": 0, "sensor_mode": 1,
    "ripple": False, "angle_snap": False, "motion_sync": True,
    "debounce": 8, "sleep": 60,
    "stages": 6, "stage": 1, "dpi": [400, 800, 1600, 3200, 6400, 26000],
    "dpi_light": 0, "dpi_extra": (1, 1),
    "fire_times": 3, "fire_speed": 10,
    "keys": [LEFT_CLICK, 0x00F10001, 0x00F20001, 0x00F30001, 0x00F40001,
             0x00030007],
    "macros": [None] * 6,
}

hid = ctypes.WinDLL("hid")
setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INVALID_HANDLE = ctypes.c_void_p(-1).value
ERROR_IO_PENDING = 997
WAIT_TIMEOUT = 0x102


class MouseError(Exception):
    """The mouse could not be reached, or did not take a setting."""


class GUID(ctypes.Structure):
    _fields_ = [("a", wt.DWORD), ("b", wt.WORD), ("c", wt.WORD),
                ("d", ctypes.c_ubyte * 8)]


class InterfaceData(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("guid", GUID), ("flags", wt.DWORD),
                ("reserved", ctypes.c_void_p)]


class Attributes(ctypes.Structure):
    _fields_ = [("Size", wt.ULONG), ("VendorID", wt.USHORT),
                ("ProductID", wt.USHORT), ("VersionNumber", wt.USHORT)]


class Caps(ctypes.Structure):
    _fields_ = [("Usage", wt.USHORT), ("UsagePage", wt.USHORT),
                ("InputReportByteLength", wt.USHORT),
                ("OutputReportByteLength", wt.USHORT),
                ("FeatureReportByteLength", wt.USHORT),
                ("Reserved", wt.USHORT * 17), ("Counts", wt.USHORT * 10)]


class Overlapped(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p),
                ("Offset", wt.DWORD), ("OffsetHigh", wt.DWORD),
                ("hEvent", ctypes.c_void_p)]


setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), wt.LPCWSTR, wt.HWND, wt.DWORD]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID), wt.DWORD,
    ctypes.POINTER(InterfaceData)]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(InterfaceData), ctypes.c_void_p, wt.DWORD,
    ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
kernel32.CreateFileW.restype = ctypes.c_void_p
kernel32.CreateFileW.argtypes = [
    wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD,
    ctypes.c_void_p]
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CreateEventW.restype = ctypes.c_void_p
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
kernel32.SetEvent.argtypes = [ctypes.c_void_p]
kernel32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD,
                              ctypes.c_void_p, ctypes.POINTER(Overlapped)]
kernel32.WriteFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD,
                               ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
kernel32.GetOverlappedResult.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(Overlapped), ctypes.POINTER(wt.DWORD), wt.BOOL]
kernel32.WaitForMultipleObjects.argtypes = [
    wt.DWORD, ctypes.POINTER(ctypes.c_void_p), wt.BOOL, wt.DWORD]
kernel32.CancelIo.argtypes = [ctypes.c_void_p]
kernel32.CreateMutexW.restype = ctypes.c_void_p
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wt.DWORD]
kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
hid.HidD_GetAttributes.argtypes = [ctypes.c_void_p, ctypes.POINTER(Attributes)]
hid.HidD_GetAttributes.restype = wt.BOOLEAN
hid.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p,
                                      ctypes.POINTER(ctypes.c_void_p)]
hid.HidD_GetPreparsedData.restype = wt.BOOLEAN
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(Caps)]
hid.HidP_GetValueCaps.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                  ctypes.POINTER(wt.USHORT), ctypes.c_void_p]
for _f in (hid.HidD_SetFeature, hid.HidD_GetFeature):
    _f.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.ULONG]
    _f.restype = wt.BOOLEAN


# -- finding it ---------------------------------------------------------------

def hid_paths():
    """The device path of every HID collection that is plugged in."""
    guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(guid))
    # DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    devs = setupapi.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, 0x12)
    try:
        index = 0
        while True:
            data = InterfaceData()
            data.cbSize = ctypes.sizeof(InterfaceData)
            if not setupapi.SetupDiEnumDeviceInterfaces(
                    devs, None, ctypes.byref(guid), index, ctypes.byref(data)):
                return
            index += 1
            need = wt.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                devs, ctypes.byref(data), None, 0, ctypes.byref(need), None)
            detail = ctypes.create_string_buffer(need.value)
            # cbSize of SP_DEVICE_INTERFACE_DETAIL_DATA_W: 8 on 64-bit, 6 on 32.
            struct.pack_into("I", detail, 0, 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6)
            if setupapi.SetupDiGetDeviceInterfaceDetailW(
                    devs, ctypes.byref(data), detail, need, None, None):
                yield ctypes.wstring_at(ctypes.addressof(detail) + 4)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(devs)


def locate():
    """(path, link, report id, report length) of the settings collection, or
    None when no Nova X21 is plugged in.

    Located by USB VID:PID and usage page, never by position: the receiver
    shows up as eight HID collections and Windows numbers them as it likes.
    """
    for path in hid_paths():
        # Windows owns the mouse and keyboard collections and refuses to
        # open them; the names alone tell ours apart, and asking costs less.
        if "vid_093a" not in path.lower():
            continue
        # No access asked for: enough to read what Windows already knows.
        handle = kernel32.CreateFileW(path, 0, 3, None, 3, 0, None)
        if handle in (None, INVALID_HANDLE):
            continue
        try:
            attr = Attributes(Size=ctypes.sizeof(Attributes))
            if not hid.HidD_GetAttributes(handle, ctypes.byref(attr)):
                continue
            link = DEVICES.get((attr.VendorID, attr.ProductID))
            if not link:
                continue
            parsed = ctypes.c_void_p()
            if not hid.HidD_GetPreparsedData(handle, ctypes.byref(parsed)):
                continue
            try:
                caps = Caps()
                hid.HidP_GetCaps(parsed, ctypes.byref(caps))
                if caps.UsagePage != USAGE_PAGE or not caps.FeatureReportByteLength:
                    continue
                # HIDP_VALUE_CAPS is 72 bytes; the report id is its third.
                count = wt.USHORT(caps.Counts[8])
                values = ctypes.create_string_buffer(72 * max(1, count.value))
                hid.HidP_GetValueCaps(2, values, ctypes.byref(count), parsed)
                return path, link, values.raw[2], caps.FeatureReportByteLength
            finally:
                hid.HidD_FreePreparsedData(parsed)
        finally:
            kernel32.CloseHandle(handle)
    return None


# -- asking and telling -------------------------------------------------------

class Turn:
    """A turn at talking to the mouse: `with mouse.turn:`.

    An answer belongs to the request before it, so only one conversation
    may run at a time -- among the threads of one program (the lock) and
    among programs (the Windows mutex: the tray icon and the settings window
    are two). A thread that has the turn may take it again inside it, which
    is how a whole read or a whole Apply is kept as one.
    """

    def __init__(self):
        self.lock = threading.RLock()
        self.mutex = kernel32.CreateMutexW(None, False, "Local\\CrystalXNovaTalk")

    def take(self, patience):
        """Take the turn if it comes free within `patience` seconds."""
        if not self.lock.acquire(timeout=patience):
            return False
        # 0: it is ours. 0x80: ours, left behind by a program that died.
        if kernel32.WaitForSingleObject(self.mutex, int(patience * 1000)) in (0, 0x80):
            return True
        self.lock.release()
        return False

    def __enter__(self):
        if not self.take(30):
            raise MouseError("Another program is talking to the mouse. Close "
                             "it and try again.")

    def __exit__(self, *error):
        kernel32.ReleaseMutex(self.mutex)
        self.lock.release()

    def close(self):
        kernel32.CloseHandle(self.mutex)


class Mouse:
    """The mouse's settings channel. Closing it is the only cleanup it needs."""

    def __init__(self):
        found = locate()
        if not found:
            raise MouseError("The mouse's receiver is not plugged in.")
        self.path, self.link, self.report_id, self.length = found
        # Shared, so the mouse keeps working for everything else that has it
        # open -- Windows itself included.
        self.handle = kernel32.CreateFileW(
            self.path, 0xC0000000, 3, None, 3, 0, None)
        if self.handle in (None, INVALID_HANDLE):
            raise MouseError(f"Could not open the mouse (Windows error "
                             f"{ctypes.get_last_error()}).")
        self.turn = Turn()

    def _send(self, body):
        out = bytes([self.report_id, *body]).ljust(self.length, b"\0")
        if not hid.HidD_SetFeature(self.handle, out, self.length):
            raise MouseError("The mouse's receiver was unplugged.")

    def ask(self, *body, wait=REPLY_WAIT, tries=3):
        """Send a read command; return the answer's bytes, or None.

        The answer starts with the report id and repeats the command after
        it. Anything else means the mouse did not answer: it is switched off,
        asleep or out of range.
        """
        if not body[0] & 0x80:
            raise ValueError(f"{body[0]:#04x} is not a read command")
        echo = bytes(body)
        with self.turn:
            for _ in range(tries):
                self._send(body)
                time.sleep(wait)
                reply = ctypes.create_string_buffer(self.length)
                reply[0] = self.report_id
                if not hid.HidD_GetFeature(self.handle, reply, self.length):
                    raise MouseError("The mouse's receiver was unplugged.")
                if reply.raw[1:1 + len(echo)] == echo:
                    return reply.raw
                wait = STATUS_WAIT
        return None

    def tell(self, *body):
        """Send a write command. The mouse does not acknowledge one."""
        if body[0] & 0x80:
            raise ValueError(f"{body[0]:#04x} is not a write command")
        with self.turn:
            self._send(body)

    def change(self, what, read, value):
        """Write `value` (bytes) where `read` reads it, and check it took.

        `read` is the read command with its arguments; the write is the same
        with the top bit clear and the value after it.
        """
        value = bytes(value)
        got = None
        for _ in range(2):
            self.tell(read[0] & WRITE, *read[1:], *value)
            time.sleep(WRITE_WAIT)
            # The mouse says nothing while it saves, which for a macro takes
            # a moment; keep asking for a while before giving up on it.
            deadline = time.monotonic() + 3
            reply = self.ask(*read)
            while reply is None and time.monotonic() < deadline:
                time.sleep(0.1)
                reply = self.ask(*read, tries=1)
            if reply is None:
                raise MouseError("The mouse stopped answering. Move it to "
                                 "wake it up, then try again.")
            got = reply[1 + len(read):1 + len(read) + len(value)]
            if got == value:
                return
        raise MouseError(f"The mouse did not take the new {what} "
                         f"(sent {value.hex(' ')}, it has {got.hex(' ')}).")

    def _macro_piece(self, key, piece):
        self._send((GET_MACRO, MACRO_PIECES, piece, MACRO_PIECE, key))
        time.sleep(WRITE_WAIT)
        reply = ctypes.create_string_buffer(1 + MACRO_PIECE)
        reply[0] = self.report_id
        if not hid.HidD_GetFeature(self.handle, reply, len(reply)):
            raise MouseError("The mouse's receiver was unplugged.")
        return reply.raw[1:]

    def read_macro(self, key, expect=None):
        """The 320 bytes the mouse holds as the macro of `key`.

        Ten pieces of 32. Each is asked for with a feature report and comes
        back in one made as long as a piece, which is longer than the mouse's
        other answers; it carries the bytes alone, with no command repeated.

        The first piece can't be trusted on one reading: about one time in
        three the mouse answers it with its first 8 bytes missing, the rest
        moved up and zeros at the end. (Measured on the real mouse; the other
        nine pieces never did it.) So it is read until two answers show
        which is the whole one, or until it is `expect`, when the caller
        knows what should be there.
        """
        with self.turn:
            seen, first = [], None
            for _ in range(8):
                got = self._macro_piece(key, 0)
                if expect is not None and got == expect[:MACRO_PIECE]:
                    first = got
                for other in seen:
                    if got[:24] == other[8:] and got != other:
                        first = other       # `got` is `other` cut short
                    elif other[:24] == got[8:] and got != other:
                        first = got
                seen.append(got)
                # Three the same, and it looks like the start of a macro
                # (its key, its mode) or like an empty one.
                if first is None and seen.count(got) >= 3 and (
                        len(set(got)) == 1
                        or got[0] == key and got[1] < len(MACRO_MODES)):
                    first = got
                if first is not None:
                    break
            if first is None:
                first = max(set(seen), key=seen.count)
            return first + b"".join(self._macro_piece(key, piece)
                                    for piece in range(1, MACRO_PIECES))

    def send_macro(self, key, data):
        """Hand the mouse `data` (see macro_bytes) as the macro of `key`.

        Each piece is announced with a feature report and then sent as an
        output report, with the pauses the vendor app leaves around them.
        The mouse only keeps it once the key is then set to play its macro
        (see set_macro).
        """
        with self.turn:
            for piece in range(MACRO_PIECES):
                self._send((GET_MACRO & WRITE, MACRO_PIECES, piece, MACRO_PIECE, key))
                time.sleep(0.040)
                out = bytes([self.report_id]) + data[piece * MACRO_PIECE:][:MACRO_PIECE]
                sent = wt.DWORD()
                if not kernel32.WriteFile(self.handle, out, len(out),
                                          ctypes.byref(sent), None):
                    raise MouseError("The mouse's receiver was unplugged.")
                time.sleep(0.060)

    def set_macro(self, key, data):
        """Make `key` play the macro in `data`, and check the mouse kept it."""
        value = macro_key(key).to_bytes(4, "little")
        for _ in range(2):
            with self.turn:
                self.send_macro(key, data)
                time.sleep(0.050)
                self.change(KEYS[key], (GET_KEY, key), value)
                for _ in range(2):
                    if self.read_macro(key, expect=data) == data:
                        return
                    time.sleep(0.5)
        raise MouseError(f"The mouse did not take the macro of the {KEYS[key]}. "
                         "Move it to wake it up, then try again.")

    def online(self, patience=2.0):
        """True when the mouse itself answers through the receiver.

        A mouse that has only just been moved takes a moment to find its
        receiver again, so this keeps asking for `patience` seconds.
        """
        deadline = time.monotonic() + patience
        while True:
            reply = self.ask(GET_STATUS, wait=STATUS_WAIT, tries=1)
            if reply and reply[2] == 3:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def close(self):
        kernel32.CloseHandle(self.handle)
        self.turn.close()


def awake():
    """Whether the mouse answers right now: True, or False when it is asleep,
    switched off or out of range. None when that can't be found out -- the
    receiver is unplugged, or another conversation with the mouse is under
    way, which this never interrupts.

    The mouse's own reports (see Listener) stop both when it sleeps and
    while it is being moved, so silence alone does not say which. This asks
    it one question, and a sleeping mouse does not answer.
    """
    try:
        mouse = Mouse()
    except MouseError:
        return None
    try:
        # The icon and the window both get here at the same moment (the same
        # silence ends for both), so wait out the other's one question -- but
        # not something long, like an Apply.
        if not mouse.turn.take(1.0):
            return None
        try:
            return mouse.ask(GET_REPORT_RATE, tries=2) is not None
        finally:
            mouse.turn.__exit__()
    except MouseError:
        return None
    finally:
        mouse.close()


# -- macros -------------------------------------------------------------------
#
# A macro here is {"name": text, "mode": one of the MACRO_ numbers,
# "count": how many times (for MACRO_TIMES), "steps": [...]}, and a step is
# ("down", key name), ("up", key name) or ("wait", milliseconds).

def is_macro(value):
    return value & 0xFF == MACRO_KIND


def macro_key(key):
    """What a key is set to so that it plays its macro. The number in it is
    the vendor app's own for the key, which swaps the two side buttons."""
    return MACRO_KIND | (0, 1, 2, 4, 3)[key] << 16


def tidy_steps(steps):
    """`steps` in the only shape the mouse can hold: no wait at the end,
    never two waits in a row."""
    out = []
    for kind, value in steps:
        if kind == "wait" and out and out[-1][0] == "wait":
            out[-1] = ("wait", min(MACRO_MAX_WAIT, out[-1][1] + value))
        else:
            out.append((kind, value))
    while out and out[-1][0] == "wait":
        out.pop()
    return out


def check_macro(macro):
    """Raise ValueError, in plain words, if the mouse can't hold this macro."""
    steps = macro["steps"]
    if not any(kind != "wait" for kind, _ in steps):
        raise ValueError("A macro needs at least one key.")
    if sum(kind != "wait" for kind, _ in steps) > MACRO_MAX_KEYS:
        raise ValueError(f"A macro can hold {MACRO_MAX_KEYS} key steps at most "
                         "(each press and each release is one step).")
    for kind, value in steps:
        if kind == "wait":
            if not 1 <= value <= MACRO_MAX_WAIT:
                raise ValueError(f"A wait must be 1 to {MACRO_MAX_WAIT} ms.")
        elif kind not in ("down", "up"):
            raise ValueError("A macro step must be a press, a release or a wait.")
        elif value not in MACRO_KEYS:
            raise ValueError(f"A macro can't use the key {value!r}.")
    if macro["mode"] not in range(len(MACRO_MODES)):
        raise ValueError("Unknown way of repeating the macro.")
    if not 1 <= macro["count"] <= MACRO_MAX_COUNT:
        raise ValueError(f"A macro can repeat 1 to {MACRO_MAX_COUNT} times.")
    if steps != tidy_steps(steps):
        raise ValueError("A macro can't end with a wait, or have two waits "
                         "in a row.")


def macro_bytes(key, macro):
    """The 320 bytes that store `macro` on `key`, laid out as the vendor app
    lays them out.

    Four bytes head it: the key, the mode, the repeat count. Then one record
    of four bytes per key step: flags, key code, and a wait in ms. A wait
    step is not a record of its own: it is written into the key step before
    it (flag 1). A key step with no wait after it gets 10 ms (flag 2), as
    the vendor app gives it. Flag 0x80 marks a press; a release has none.
    The last 32 bytes are the vendor app's own notes -- the name, sizes --
    kept so that it can still read a macro written here.
    """
    data = bytearray(MACRO_BYTES)
    data[0], data[1] = key, macro["mode"]
    data[2:4] = macro["count"].to_bytes(2, "little")
    steps = macro["steps"]
    at, before = 4, None
    for index, (kind, value) in enumerate(steps):
        if kind == "wait":
            data[at + 2:at + 4] = value.to_bytes(2, "little")
            if index == 0:
                data[at] = 4            # a wait before anything is pressed
            else:
                data[at] |= 1
            at += 4
        else:
            if before != "wait" and index:
                data[at] |= 2
                data[at + 2:at + 4] = (10).to_bytes(2, "little")
                at += 4
            data[at] = 0x80 if kind == "down" else 0
            data[at + 1] = MACRO_KEYS[value]
            if kind == "down":
                data[at + 2] = 8
        before = kind
    name = macro["name"].encode("ascii", "replace")[:15]
    data[MACRO_NAME:MACRO_NAME + len(name)] = name
    struct.pack_into("<IIIHH", data, MACRO_TRAILER, len(steps) * 4 + 0x70, 0,
                     key + 1, len(steps) + 1, at // 4)
    return bytes(data)


def macro_from_bytes(data):
    """The macro stored in 320 bytes read from the mouse, or None if they
    hold none."""
    records = min(struct.unpack_from("<H", data, MACRO_TRAILER + 14)[0], 0x47)
    steps = []
    for record in range(1, records + 1):
        flags, code, wait = struct.unpack_from("<BBH", data, record * 4)
        if record == 1 and flags == 4:
            steps.append(("wait", wait))
            continue
        if code not in MACRO_KEY_NAMES:
            continue
        steps.append(("down" if flags & 0x80 else "up", MACRO_KEY_NAMES[code]))
        if flags & 0x7F == 1 and wait:
            steps.append(("wait", wait))
    steps = tidy_steps(steps)
    if not any(kind != "wait" for kind, _ in steps):
        return None
    name = data[MACRO_NAME:MACRO_TRAILER].split(b"\0")[0].decode("ascii", "replace")
    mode = data[1] if data[1] < len(MACRO_MODES) else MACRO_TIMES
    return {"name": name, "mode": mode, "steps": steps,
            "count": min(MACRO_MAX_COUNT, max(1, data[2] | data[3] << 8))}


def describe_macro(macro):
    """A macro in one line of words."""
    words = {"down": "press", "up": "release"}
    steps = ", ".join(f"wait {value} ms" if kind == "wait" else f"{words[kind]} {value}"
                      for kind, value in macro["steps"])
    repeat = MACRO_MODES[macro["mode"]]
    if macro["mode"] == MACRO_TIMES:
        repeat = "once" if macro["count"] == 1 else f"{macro['count']} times"
    return f"{macro['name'] or 'macro'} ({repeat}): {steps}"


# -- the settings -------------------------------------------------------------

def dpi_code(dpi):
    return dpi // DPI_STEP - 1


def read_settings(mouse):
    """Everything the mouse holds, as a dict shaped like DEFAULTS."""
    with mouse.turn:
        return _read_settings(mouse)


def _read_settings(mouse):
    silent = MouseError("The mouse is not answering. Move it to wake it up, "
                        "and check it is switched on.")

    def need(*body):
        reply = mouse.ask(*body)
        if reply is None:
            raise silent
        return reply

    if not mouse.online():
        raise silent
    rate = need(GET_REPORT_RATE)[2]
    setup = need(GET_DPI_SETUP)
    sensor = {which: need(GET_SENSOR, which)[3] for which in range(1, 6)}
    sleep = need(GET_OPTION, SLEEP)
    fire = need(GET_OPTION, FIRE_OPTION)
    keys = [int.from_bytes(need(GET_KEY, i)[3:7], "little") for i in range(len(KEYS))]
    return {
        "rate": {code: hz for hz, code in RATES.items()}.get(rate, 1000),
        "lod": sensor[LOD], "sensor_mode": sensor[SENSOR_MODE],
        "ripple": bool(sensor[RIPPLE]), "angle_snap": bool(sensor[ANGLE_SNAP]),
        "motion_sync": bool(sensor[MOTION_SYNC]),
        "debounce": need(GET_OPTION, DEBOUNCE)[3],
        "sleep": sleep[3] | sleep[4] << 8,
        "stages": setup[2], "stage": setup[3], "dpi_light": setup[4],
        "dpi_extra": (setup[5], setup[6]),
        "dpi": [(int.from_bytes(need(GET_DPI_STAGE, i)[3:5], "little") + 1) * DPI_STEP
                for i in range(STAGES)],
        "fire_times": fire[3], "fire_speed": fire[4],
        "keys": keys,
        # Reading a macro takes a second, so only where a key plays one.
        "macros": [macro_from_bytes(mouse.read_macro(i))
                   if i < ASSIGNABLE and is_macro(value) else None
                   for i, value in enumerate(keys)],
    }


def check(settings):
    """Raise ValueError, in plain words, if the mouse can't be set like this."""
    s = settings
    if s["rate"] not in RATES:
        raise ValueError(f"The report rate must be one of "
                         f"{', '.join(map(str, RATES))} Hz.")
    for name, key, choices in (("lift-off distance", "lod", LODS),
                               ("sensor mode", "sensor_mode", SENSOR_MODES)):
        if s[key] not in range(len(choices)):
            raise ValueError(f"Unknown {name}.")
    if not 0 <= s["debounce"] <= DEBOUNCE_MAX:
        raise ValueError(f"Debounce must be 0 to {DEBOUNCE_MAX} ms.")
    if s["sleep"] not in SLEEP_TIMES:
        raise ValueError("That sleep time is not one the mouse offers.")
    if not 1 <= s["stages"] <= STAGES:
        raise ValueError(f"The mouse has 1 to {STAGES} DPI stages.")
    if not 0 <= s["stage"] < s["stages"]:
        raise ValueError("The DPI stage in use must be one of the stages "
                         "switched on.")
    for dpi in s["dpi"]:
        if not DPI_MIN <= dpi <= DPI_MAX or dpi % DPI_STEP:
            raise ValueError(f"DPI must be {DPI_MIN} to {DPI_MAX}, in steps "
                             f"of {DPI_STEP}.")
    if not 0 <= s["fire_times"] <= FIRE_TIMES_MAX:
        raise ValueError(f"Fire clicks must be 0 to {FIRE_TIMES_MAX}.")
    if not 0 <= s["fire_speed"] <= FIRE_SPEED_MAX:
        raise ValueError(f"Fire speed must be 0 to {FIRE_SPEED_MAX}.")
    if len(s["dpi"]) != STAGES or len(s["keys"]) != len(KEYS) \
            or len(s["macros"]) != len(KEYS):
        raise ValueError("Incomplete settings.")
    # Without this the pointer can no longer click anything, including the
    # button that would undo it.
    if LEFT_CLICK not in s["keys"]:
        raise ValueError("At least one button must stay set to Left click.")
    for i, value in enumerate(s["keys"][:ASSIGNABLE]):
        if is_macro(value):
            # A key can only play the macro stored under its own number.
            if value != macro_key(i) or not s["macros"][i]:
                raise ValueError(f"The {KEYS[i]} is set to a macro, but has none.")
            check_macro(s["macros"][i])


def apply(mouse, old, new, step=None):
    """Send the mouse what differs between `old` and `new`; return how many
    settings were sent. Each is read back, and MouseError says which one the
    mouse did not take.

    Only what changed is sent, so a change to one setting does not rewrite
    the others. `step(text)` is called before each.
    """
    check(new)
    with mouse.turn:
        return _apply(mouse, old, new, step)


def _apply(mouse, old, new, step):
    sent = 0

    def change(what, read, value):
        nonlocal sent
        if step:
            step(what)
        mouse.change(what, read, value)
        sent += 1

    if new["rate"] != old["rate"]:
        change("report rate", (GET_REPORT_RATE,), [RATES[new["rate"]]])
    for i, dpi in enumerate(new["dpi"]):
        if dpi != old["dpi"][i]:
            change(f"DPI of stage {i + 1}", (GET_DPI_STAGE, i),
                   dpi_code(dpi).to_bytes(2, "little"))
    setup = ("stages", "stage", "dpi_light", "dpi_extra")
    if any(new[k] != old[k] for k in setup):
        change("DPI stages", (GET_DPI_SETUP,),
               [new["stages"], new["stage"], new["dpi_light"], *new["dpi_extra"]])
    for what, key, which in (("lift-off distance", "lod", LOD),
                             ("ripple control", "ripple", RIPPLE),
                             ("angle snapping", "angle_snap", ANGLE_SNAP),
                             ("motion sync", "motion_sync", MOTION_SYNC),
                             ("sensor mode", "sensor_mode", SENSOR_MODE)):
        if new[key] != old[key]:
            change(what, (GET_SENSOR, which), [int(new[key])])
    if new["debounce"] != old["debounce"]:
        change("debounce", (GET_OPTION, DEBOUNCE), [new["debounce"]])
    if new["sleep"] != old["sleep"]:
        change("sleep time", (GET_OPTION, SLEEP), new["sleep"].to_bytes(2, "little"))
    if (new["fire_times"], new["fire_speed"]) != (old["fire_times"], old["fire_speed"]):
        change("fire settings", (GET_OPTION, FIRE_OPTION),
               [new["fire_times"], new["fire_speed"]])
    for i, value in enumerate(new["keys"][:ASSIGNABLE]):
        if is_macro(value):
            # The macro and the key go together, in that order: the mouse
            # keeps a macro only when its key is then set to play it.
            if new["macros"][i] != old["macros"][i] or value != old["keys"][i]:
                if step:
                    step(f"macro of the {KEYS[i]}")
                mouse.set_macro(i, macro_bytes(i, new["macros"][i]))
                sent += 1
        elif value != old["keys"][i]:
            change(KEYS[i], (GET_KEY, i), value.to_bytes(4, "little"))
    return sent


# -- what a key does ----------------------------------------------------------

def shortcut(modifiers, key):
    """The key value for a keyboard shortcut: modifier bits and a key name
    from KEY_CODES ("" for the modifiers alone)."""
    return modifiers << 8 | KEY_CODES.get(key, 0) << 16


def shortcut_parts(value):
    """(modifier bits, key name) of a keyboard shortcut, or None if `value`
    is not one this can show whole."""
    kind, modifiers, key, second = value.to_bytes(4, "little")
    if kind or not value or second or (key and key not in KEY_NAMES):
        return None
    return modifiers, KEY_NAMES.get(key, "")


def describe_key(value):
    """What a key does, in words."""
    if value in FUNCTION_NAMES:
        return FUNCTION_NAMES[value]
    if is_macro(value):
        return "Macro"
    parts = shortcut_parts(value)
    if parts:
        names = [name for name, bit in MODIFIERS if parts[0] & bit]
        return " + ".join(names + ([parts[1]] if parts[1] else []))
    return f"Other ({value.to_bytes(4, 'little').hex(' ')})"


def key_from_text(text, key):
    """The opposite of describe_key, for key number `key`. ValueError if the
    text names nothing a key can do."""
    values = {name: value for name, value in FUNCTIONS}
    if text in values:
        return values[text]
    if text == "Macro":
        return macro_key(key)
    if text.startswith("Other (") and text.endswith(")"):
        try:
            raw = bytes.fromhex(text[7:-1])
        except ValueError:
            raw = b""
        if len(raw) == 4:
            return int.from_bytes(raw, "little")
    bits, name = 0, ""
    for part in text.split(" + "):
        if part in dict(MODIFIERS) and not name:
            bits |= dict(MODIFIERS)[part]
        elif part in KEY_CODES and not name:
            name = part
        else:
            raise ValueError(f"{text!r} is not something a button can do.")
    return shortcut(bits, name)


# -- profile files ------------------------------------------------------------

def profile_text(settings):
    """`settings` as the text of a profile file: JSON, with names a person
    can read and change by hand."""
    import json
    s = settings
    macros = {KEYS[i]: {"name": m["name"],
                        "repeat": MACRO_MODES[m["mode"]], "times": m["count"],
                        "steps": [f"{kind} {value}" for kind, value in m["steps"]]}
              for i, m in enumerate(s["macros"]) if m and is_macro(s["keys"][i])}
    return json.dumps({
        "program": DISPLAY_NAME, "profile": 1,
        "report_rate_hz": s["rate"],
        "lift_off_distance": LODS[s["lod"]],
        "sensor_mode": SENSOR_MODES[s["sensor_mode"]],
        "motion_sync": s["motion_sync"], "angle_snapping": s["angle_snap"],
        "ripple_control": s["ripple"],
        "debounce_ms": s["debounce"], "sleep_after_seconds": s["sleep"],
        "dpi_stages_in_use": s["stages"], "dpi_stage_in_use": s["stage"] + 1,
        "dpi": s["dpi"],
        "fire_clicks": s["fire_times"], "fire_speed": s["fire_speed"],
        "buttons": {KEYS[i]: describe_key(value)
                    for i, value in enumerate(s["keys"][:ASSIGNABLE])},
        "macros": macros,
    }, indent=2)


def profile_settings(text, base):
    """The settings in a profile file's text. What the file leaves out stays
    as in `base`. ValueError, in plain words, if the file is not usable."""
    import json
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if not isinstance(data, dict) or data.get("program") != DISPLAY_NAME:
        raise ValueError("This is not a profile file of this app.")
    s = {**base, "dpi": list(base["dpi"]), "keys": list(base["keys"]),
         "macros": list(base["macros"])}
    try:
        for name, key, kind in (("report_rate_hz", "rate", int),
                                ("motion_sync", "motion_sync", bool),
                                ("angle_snapping", "angle_snap", bool),
                                ("ripple_control", "ripple", bool),
                                ("debounce_ms", "debounce", int),
                                ("sleep_after_seconds", "sleep", int),
                                ("dpi_stages_in_use", "stages", int),
                                ("fire_clicks", "fire_times", int),
                                ("fire_speed", "fire_speed", int)):
            if name in data:
                if type(data[name]) is not kind:
                    raise ValueError(f"{name} has a value this app can't use.")
                s[key] = data[name]
        if "dpi_stage_in_use" in data:
            s["stage"] = int(data["dpi_stage_in_use"]) - 1
        if "lift_off_distance" in data:
            s["lod"] = LODS.index(data["lift_off_distance"])
        if "sensor_mode" in data:
            s["sensor_mode"] = SENSOR_MODES.index(data["sensor_mode"])
        if "dpi" in data:
            s["dpi"] = [int(v) for v in data["dpi"]]
        for i, name in enumerate(KEYS[:ASSIGNABLE]):
            if name in data.get("buttons", {}):
                s["keys"][i] = key_from_text(data["buttons"][name], i)
            macro = data.get("macros", {}).get(name)
            if macro:
                s["macros"][i] = {
                    "name": str(macro.get("name", "")),
                    "mode": MACRO_MODES.index(macro.get("repeat", MACRO_MODES[MACRO_TIMES])),
                    "count": int(macro.get("times", 1)),
                    "steps": [(kind, int(value) if kind == "wait" else value)
                              for kind, _, value in
                              (line.partition(" ") for line in macro["steps"])]}
    except (TypeError, KeyError, AttributeError) as e:
        raise ValueError("The profile file is damaged.") from e
    except ValueError as e:
        if "can't use" in str(e) or "button can do" in str(e):
            raise
        raise ValueError("The profile file has a value this app can't use.") from e
    check(s)
    return s


# -- what the mouse says by itself --------------------------------------------

class Status:
    """One of the reports the mouse sends every few seconds while awake."""

    def __init__(self, data):
        self.battery = data[1] & 0x7F           # percent
        self.charging = bool(data[1] & 0x80)
        self.stage = data[2] >> 4               # DPI stage in use, from 0
        self.rate = {code: hz for hz, code in RATES.items()}.get(data[2] & 0x0F)
        self.debounce = data[3] & 0x7F
        self.lod = data[7] >> 4
        self.motion_sync = bool(data[7] & 0x0F)


class Listener:
    """Waits for the mouse's own reports. Costs nothing while it waits: the
    thread sleeps inside Windows until a report arrives.

    `wait()` gives a Status, None after `quiet` seconds without one (the
    mouse is asleep, switched off or out of range), or raises MouseError
    when the receiver is unplugged or `stop()` was called.
    """

    LENGTH = 33

    def __init__(self):
        found = locate()
        if not found:
            raise MouseError("The mouse's receiver is not plugged in.")
        self.link = found[1]
        self.report_id = found[2]
        # GENERIC_READ, shared, FILE_FLAG_OVERLAPPED
        self.handle = kernel32.CreateFileW(
            found[0], 0x80000000, 3, None, 3, 0x40000000, None)
        if self.handle in (None, INVALID_HANDLE):
            raise MouseError(f"Could not open the mouse (Windows error "
                             f"{ctypes.get_last_error()}).")
        self.arrived = kernel32.CreateEventW(None, True, False, None)
        self.stopped = kernel32.CreateEventW(None, True, False, None)
        self.events = (ctypes.c_void_p * 2)(self.arrived, self.stopped)
        self.buffer = ctypes.create_string_buffer(self.LENGTH)
        self.pending = None

    def wait(self, quiet=20.0):
        while True:
            if self.pending is None:
                self.pending = Overlapped()
                self.pending.hEvent = self.arrived
                if not kernel32.ReadFile(self.handle, self.buffer, self.LENGTH,
                                         None, ctypes.byref(self.pending)) \
                        and ctypes.get_last_error() != ERROR_IO_PENDING:
                    raise MouseError("The mouse's receiver was unplugged.")
            which = kernel32.WaitForMultipleObjects(
                2, self.events, False, int(quiet * 1000))
            if which == WAIT_TIMEOUT:
                return None
            if which != 0:
                raise MouseError("Stopped.")
            got = wt.DWORD()
            done = kernel32.GetOverlappedResult(
                self.handle, ctypes.byref(self.pending), ctypes.byref(got), False)
            self.pending = None
            if not done:
                raise MouseError("The mouse's receiver was unplugged.")
            if got.value >= 8 and self.buffer.raw[0] == self.report_id:
                return Status(self.buffer.raw)

    def stop(self):
        """Make a `wait()` under way on another thread give up."""
        kernel32.SetEvent(self.stopped)

    def close(self):
        # Call on the thread that waits: Windows cancels a read only for the
        # thread that started it.
        kernel32.CancelIo(self.handle)
        for handle in (self.handle, self.arrived, self.stopped):
            kernel32.CloseHandle(handle)


# -- command line -------------------------------------------------------------

def describe(settings):
    s = settings
    lines = [
        f"Report rate        {s['rate']} Hz",
        f"Lift-off distance  {LODS[s['lod']]}",
        f"Sensor mode        {SENSOR_MODES[s['sensor_mode']]}",
        f"Motion sync        {'on' if s['motion_sync'] else 'off'}",
        f"Angle snapping     {'on' if s['angle_snap'] else 'off'}",
        f"Ripple control     {'on' if s['ripple'] else 'off'}",
        f"Debounce           {s['debounce']} ms",
        f"Sleep after        {s['sleep']} s",
        f"Fire               {s['fire_times']} clicks, speed {s['fire_speed']}",
    ]
    for i, dpi in enumerate(s["dpi"]):
        note = " (in use)" if i == s["stage"] else "" if i < s["stages"] else " (off)"
        lines.append(f"DPI stage {i + 1}        {dpi}{note}")
    for i, (name, value) in enumerate(zip(KEYS, s["keys"])):
        does = describe_key(value)
        if is_macro(value) and s["macros"][i]:
            does = "Macro - " + describe_macro(s["macros"][i])
        lines.append(f"{name:<18} {does}")
    return "\n".join(lines)


def parse_set(pairs, settings):
    """Apply name=value pairs from the command line to a copy of `settings`."""
    new = {**settings, "dpi": list(settings["dpi"])}
    for pair in pairs:
        name, _, text = pair.partition("=")
        if name in ("ripple", "angle_snap", "motion_sync"):
            new[name] = text.lower() in ("1", "on", "true", "yes")
        elif name in ("rate", "lod", "sensor_mode", "debounce", "sleep",
                      "stages", "fire_times", "fire_speed"):
            new[name] = int(text)
        elif name == "stage":
            new[name] = int(text) - 1
        elif name[:3] == "dpi" and name[3:] in "123456" and len(name) == 4:
            new["dpi"][int(name[3]) - 1] = int(text)
        else:
            sys.exit(f"unknown setting: {name}")
    return new


def main():
    # Imported here: the tray icon imports this file and never needs it.
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--find", action="store_true",
                    help="only locate the mouse; send nothing")
    ap.add_argument("--watch", action="store_true",
                    help="print what the mouse reports, as it comes")
    ap.add_argument("--export", metavar="FILE",
                    help="save every setting to a profile file")
    ap.add_argument("--import", dest="load", metavar="FILE",
                    help="send a profile file to the mouse")
    ap.add_argument("--set", nargs="+", metavar="NAME=VALUE",
                    help="change settings")
    args = ap.parse_args()

    try:
        if args.find:
            found = locate()
            if not found:
                sys.exit("Nova X21 not found -- is the receiver plugged in?")
            print(f"Nova X21 on its {found[1]}: report id {found[2]:#04x}, "
                  f"{found[3]} bytes\n{found[0]}")
            return
        if args.watch:
            listener = Listener()
            while True:
                status = listener.wait()
                print("asleep, off or out of range" if status is None else
                      f"battery {status.battery}%"
                      f"{' charging' if status.charging else ''}, "
                      f"DPI stage {status.stage + 1}, {status.rate} Hz",
                      flush=True)
        mouse = Mouse()
        try:
            settings = read_settings(mouse)
            new = None
            if args.load:
                with open(args.load, encoding="utf-8") as f:
                    new = profile_settings(f.read(), settings)
            if args.set:
                new = parse_set(args.set, new or settings)
            if new:
                sent = apply(mouse, settings, new,
                             step=lambda what: print(f"setting {what}", flush=True))
                print(f"{sent} setting(s) changed and read back.\n")
                settings = read_settings(mouse)
            if args.export:
                with open(args.export, "w", encoding="utf-8") as f:
                    f.write(profile_text(settings))
                print(f"Saved to {args.export}\n")
            print(f"Nova X21 on its {mouse.link}\n{describe(settings)}")
        finally:
            mouse.close()
        listener = Listener()
        status = listener.wait(quiet=8)
        listener.close()
        print("Battery            " + ("no report yet" if status is None else
              f"{status.battery}%{' (charging)' if status.charging else ''}"))
    except (MouseError, ValueError, OSError) as e:
        sys.exit(str(e))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
