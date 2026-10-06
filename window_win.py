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
"""The settings window of the Nova X21.

It shows what the mouse holds, and Apply sends the mouse what was changed.
The mouse keeps its settings itself, so this window -- and the tray icon --
can be closed afterwards; nothing here has to stay running.

Nothing in it runs on a timer. The battery line and the DPI stage in use
follow the mouse's own reports, which a thread waits for inside Windows.

The words on screen are kept simple on purpose: short sentences and common
words, and for every setting what it does and what can go wrong with it.
Many people who use this do not have English as their first language.

Usage:
    window_win.py
"""

import ctypes
import os
import sys
import threading
import tkinter as tk
import winreg
from tkinter import messagebox, ttk

import mouse_win
from mouse_win import (ASSIGNABLE, DEFAULTS, DISPLAY_NAME, DPI_MAX, DPI_MIN,
                       DPI_STEP, DEBOUNCE_MAX, FIRE_SPEED_MAX, FIRE_TIMES_MAX,
                       FUNCTIONS, KEY_CODES, KEYS, LODS, MACRO_HELD, MACRO_KEYS,
                       MACRO_MAX_COUNT, MACRO_MAX_KEYS, MACRO_MAX_WAIT,
                       MACRO_TIMES, MACRO_TOGGLE, MODIFIERS, RATES,
                       SENSOR_MODE_MAX_RATE, SENSOR_MODES, SLEEP_TIMES, STAGES,
                       VERSION, MouseError)

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "assets", "crystalx-nova.ico")
MUTEX = "Local\\CrystalXNovaWindow"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
GREY, AMBER = "#666666", "#a85a00"
WRAP = 430                      # how wide an explanation may run, in pixels
SHORTCUT = "Keyboard shortcut..."
MACRO = "Macro..."
NO_KEY = "(none)"
# Shown smallest first; the mouse numbers them differently.
LOD_ORDER = (2, 0, 1)

# What each setting does and what it can cause, in plain words.
ABOUT_RATE = ("How many times each second the mouse tells the PC where it is. "
              "A higher number feels smoother in fast games. But above 1000 Hz "
              "the battery empties faster and the PC has to work harder.")
ABOUT_LOD = ("How high you can lift the mouse before the pointer stops moving. "
             "A low number stops it at once: good if you often lift the mouse "
             "in games. If the pointer stops or jumps on your mouse pad, "
             "choose a higher number.")
ABOUT_MODE = ("Low power: the battery lasts longest. Good for normal use.\n"
              "High performance: follows fast movement better, uses more battery.\n"
              "Corded: the strongest. It is made for use with the cable, and "
              "empties the battery fastest.")
ABOUT_MODE_FAST = (f"Above {SENSOR_MODE_MAX_RATE} Hz the mouse chooses this by "
                   "itself, so you cannot change it here.")
ABOUT_SYNC = ("The sensor measures at the same moment the mouse reports to the "
              "PC, so movement is more even. It adds a very small delay that "
              "most people cannot feel. Best left on.")
ABOUT_SNAP = ("Makes your lines straighter by ignoring small hand shakes. Good "
              "for drawing. Bad for games, because the pointer no longer "
              "follows your hand exactly. Best left off.")
ABOUT_RIPPLE = ("Makes the pointer steadier at very high DPI, but adds a small "
                "delay. Turn it on only if the pointer shakes at high DPI.")
ABOUT_DPI = ("DPI is the speed of the pointer. With a higher DPI the pointer "
             "moves further for the same hand movement. Very high numbers make "
             "the pointer hard to control.")
ABOUT_STAGES = ("The DPI button on the mouse goes through these stages, one "
                "after another. Use fewer stages if you only need one or two "
                "speeds; then you will not land on a wrong speed by accident.")
ABOUT_BUTTONS = ("At least one button must stay as Left click. Without it you "
                 "cannot click anything, not even to change it back.")
ABOUT_DPI_BUTTON = "Changes the DPI stage. This button cannot be changed."
ABOUT_FIRE = ("For a button set to Fire. Clicks: how many clicks one press "
              "makes. With 0 it keeps clicking for as long as you hold the "
              "button. Speed: a number from 0 to 255 that sets how fast the "
              "clicks come. Try it in a game or a click test to find what "
              "you like. Some online games do not allow this.")
ABOUT_DEBOUNCE = ("After a click, the mouse waits this long before it accepts "
                  "the next one. A low number makes clicks faster. But if it "
                  "is too low, one click can count as two. If that happens, "
                  "choose a higher number. 8 ms is right for most people.")
ABOUT_SLEEP = ("The mouse goes to sleep when you do not use it for this long. "
               "That saves battery. Move or click the mouse to wake it up. A "
               "short time saves more battery; a long time means the mouse "
               "is asleep less often when you come back to it.")
ABOUT_PROFILE = ("A profile is a file with every setting in this window. Save "
                 "one to keep a copy, or to change between setups. Loading "
                 "only fills in this window: click Apply to send it to the "
                 "mouse.")
ABOUT_AUTOSTART = ("The mouse works the same without the icon. Turn this on "
                   "only if you want to see the battery level all the time.")
ABOUT_MACRO = ("A macro is a list of key presses that the mouse plays when "
               "you press the button. It is stored in the mouse, so it also "
               "works when this app is closed. Some online games do not "
               "allow macros.")

# The key a Windows key code names, for recording a macro.
VK_NAMES = {
    **{0x41 + i: chr(65 + i) for i in range(26)},
    **{0x30 + i: str(i) for i in range(10)},
    **{0x70 + i: f"F{i + 1}" for i in range(12)},
    0x0D: "Enter", 0x1B: "Esc", 0x08: "Backspace", 0x09: "Tab", 0x20: "Space",
    0xBD: "-", 0xBB: "=", 0xDB: "[", 0xDD: "]", 0xDC: "\\", 0xBA: ";",
    0xDE: "'", 0xC0: "`", 0xBC: ",", 0xBE: ".", 0xBF: "/",
    0x2C: "Print Screen", 0x2D: "Insert", 0x24: "Home", 0x21: "Page Up",
    0x2E: "Delete", 0x23: "End", 0x22: "Page Down",
    0x27: "Right", 0x25: "Left", 0x28: "Down", 0x26: "Up",
    0x10: "Shift", 0xA0: "Shift", 0xA1: "Shift",
    0x11: "Ctrl", 0xA2: "Ctrl", 0xA3: "Ctrl",
    0x12: "Alt", 0xA4: "Alt", 0xA5: "Alt", 0x5B: "Win", 0x5C: "Win",
}


def sleep_text(seconds):
    if seconds < 60:
        return f"{seconds} seconds"
    return "1 minute" if seconds == 60 else f"{seconds // 60} minutes"


SLEEP_TEXTS = {sleep_text(s): s for s in SLEEP_TIMES}


def step_text(step):
    kind, value = step
    if kind == "wait":
        return f"Wait {value} ms"
    return f"{'Press' if kind == 'down' else 'Release'} {value}"


def autostart_command():
    """What Windows runs at login: the tray icon alone, with no window."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --hidden'
    # pythonw has no console window; python.exe would flash one at login.
    program = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(program):
        program = sys.executable
    return f'"{program}" "{os.path.join(HERE, "tray_win.py")}" --hidden'


def autostart_on():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, DISPLAY_NAME)
        return True
    except OSError:
        return False


def set_autostart(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, DISPLAY_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, DISPLAY_NAME)
            except FileNotFoundError:
                pass


class Dialog:
    """A small window on top of the main one; `result` stays None on Cancel."""

    def __init__(self, parent, title):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.frame = ttk.Frame(self.top, padding=14)
        self.frame.grid()
        self.top.bind("<Escape>", lambda e: self.top.destroy())

    def buttons(self, row, columns):
        bar = ttk.Frame(self.frame)
        bar.grid(row=row, column=0, columnspan=columns, sticky="e", pady=(14, 0))
        ttk.Button(bar, text="OK", command=self.ok).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Cancel", command=self.top.destroy).pack(side="left")

    def wait(self, parent):
        self.top.grab_set()
        parent.wait_window(self.top)
        return self.result


class ShortcutDialog(Dialog):
    """Pick a keyboard shortcut: any of Ctrl, Shift, Alt, Win, and a key."""

    def __init__(self, parent, value):
        super().__init__(parent, "Keyboard shortcut")
        parts = mouse_win.shortcut_parts(value) or (0, "")
        ttk.Label(self.frame, text="When you press the button, the mouse presses:").grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
        self.modifiers = []
        for column, (name, bit) in enumerate(MODIFIERS):
            var = tk.BooleanVar(value=bool(parts[0] & bit))
            ttk.Checkbutton(self.frame, text=name, variable=var).grid(
                row=1, column=column, sticky="w", padx=(0, 10))
            self.modifiers.append((var, bit))
        self.key = tk.StringVar(value=parts[1] or NO_KEY)
        ttk.Combobox(self.frame, textvariable=self.key, state="readonly", width=13,
                     values=[NO_KEY, *KEY_CODES]).grid(row=1, column=4, sticky="w")
        ttk.Label(self.frame, text="Example: tick Ctrl and choose C to copy.",
                  style="Hint.TLabel").grid(row=2, column=0, columnspan=5,
                                            sticky="w", pady=(8, 0))
        self.buttons(3, 5)
        self.top.bind("<Return>", lambda e: self.ok())
        self.wait(parent)

    def ok(self):
        bits = sum(bit for var, bit in self.modifiers if var.get())
        key = "" if self.key.get() == NO_KEY else self.key.get()
        if not bits and not key:
            messagebox.showinfo("Keyboard shortcut", "Choose a key, or at least "
                                "one of Ctrl, Shift, Alt and Win.", parent=self.top)
            return
        self.result = mouse_win.shortcut(bits, key)
        self.top.destroy()


class KeyDialog(Dialog):
    """Pick a key to add to a macro, and whether to press it, release it or
    do both."""

    def __init__(self, parent):
        super().__init__(parent, "Add a key")
        ttk.Label(self.frame, text="Key").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.key = tk.StringVar(value="A")
        ttk.Combobox(self.frame, textvariable=self.key, state="readonly", width=14,
                     values=list(MACRO_KEYS), height=16).grid(row=0, column=1, sticky="w")
        self.how = tk.StringVar(value="tap")
        for row, (value, text) in enumerate((
                ("tap", "Press and release (a normal key press)"),
                ("down", "Press and keep held"),
                ("up", "Release"))):
            ttk.Radiobutton(self.frame, text=text, variable=self.how, value=value).grid(
                row=row + 1, column=0, columnspan=2, sticky="w", pady=(8 if not row else 2, 0))
        ttk.Label(self.frame, style="Hint.TLabel", wraplength=300, justify="left",
                  text="A key that is pressed and kept held must be released "
                       "later in the macro. If not, the PC acts as if you are "
                       "still holding it.").grid(row=4, column=0, columnspan=2,
                                                 sticky="w", pady=(8, 0))
        self.buttons(5, 2)
        self.wait(parent)

    def ok(self):
        key = self.key.get()
        self.result = {"tap": [("down", key), ("wait", 30), ("up", key)],
                       "down": [("down", key)], "up": [("up", key)]}[self.how.get()]
        self.top.destroy()


class MacroDialog(Dialog):
    """Edit the macro of one button: its steps, and how it repeats."""

    def __init__(self, parent, button, macro):
        super().__init__(parent, f"Macro of the {button}")
        macro = macro or {"name": "", "mode": MACRO_TIMES, "count": 1, "steps": []}
        self.steps = list(macro["steps"])
        self.recording = False
        self.held = set()           # keys down while recording
        self.last = None            # when the last recorded step came, in ms
        f = self.frame
        ttk.Label(f, text=ABOUT_MACRO, style="Hint.TLabel", wraplength=WRAP,
                  justify="left").grid(row=0, column=0, columnspan=2, sticky="w",
                                       pady=(0, 10))
        line = ttk.Frame(f)
        line.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(line, text="Name").pack(side="left", padx=(0, 10))
        self.name = tk.StringVar(value=macro["name"])
        ttk.Entry(line, textvariable=self.name, width=22).pack(side="left")

        self.list = tk.Listbox(f, height=12, width=34, activestyle="none",
                               exportselection=False)
        self.list.grid(row=2, column=0, sticky="nsew")
        side = ttk.Frame(f)
        side.grid(row=2, column=1, sticky="n", padx=(10, 0))
        self.record_btn = ttk.Button(side, text="Record keys", width=16,
                                     command=self.toggle_record)
        self.record_btn.pack(pady=(0, 10))
        self.edit_buttons = []
        for text, command in (("Add a key...", self.add_key),
                              ("Add a wait...", self.add_wait),
                              ("Move up", lambda: self.move(-1)),
                              ("Move down", lambda: self.move(1)),
                              ("Remove", self.remove), ("Remove all", self.clear)):
            button = ttk.Button(side, text=text, width=16, command=command)
            button.pack(pady=(0, 4))
            self.edit_buttons.append(button)
        self.count_text = tk.StringVar()
        ttk.Label(f, textvariable=self.count_text, style="Hint.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.record_hint = tk.StringVar(
            value="Record keys: click it, type the keys on your keyboard, then "
                  "click Stop. The time between your key presses is recorded too.")
        ttk.Label(f, textvariable=self.record_hint, style="Hint.TLabel",
                  wraplength=WRAP, justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(2, 10))

        ttk.Label(f, text="When you press the button, play the macro:").grid(
            row=5, column=0, columnspan=2, sticky="w")
        self.mode = tk.IntVar(value=macro["mode"])
        self.count = tk.StringVar(value=str(macro["count"]))
        line = ttk.Frame(f)
        line.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Radiobutton(line, variable=self.mode, value=MACRO_TIMES).pack(side="left")
        ttk.Spinbox(line, textvariable=self.count, from_=1, to=MACRO_MAX_COUNT,
                    width=6).pack(side="left", padx=(0, 6))
        ttk.Label(line, text="time(s), then stop").pack(side="left")
        ttk.Radiobutton(f, variable=self.mode, value=MACRO_HELD,
                        text="Again and again, for as long as you hold the button").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Radiobutton(f, variable=self.mode, value=MACRO_TOGGLE,
                        text="Again and again, until you press the button a second time").grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self.buttons(9, 2)
        self.top.bind("<KeyPress>", self.key_down)
        self.top.bind("<KeyRelease>", self.key_up)
        # Esc closes the dialog, except while recording, when it is a key
        # like any other.
        self.top.bind("<Escape>", lambda e: self.key_down(e) or self.top.destroy())
        self.show()
        self.wait(parent)

    def show(self, select=None):
        self.list.delete(0, "end")
        for step in self.steps:
            self.list.insert("end", step_text(step))
        if select is not None and self.steps:
            select = max(0, min(select, len(self.steps) - 1))
            self.list.selection_set(select)
            self.list.see(select)
        keys = sum(kind != "wait" for kind, _ in self.steps)
        self.count_text.set(f"{keys} of {MACRO_MAX_KEYS} key steps used. "
                            "Each press and each release is one step; waits are free.")

    def selected(self):
        chosen = self.list.curselection()
        return chosen[0] if chosen else None

    def insert(self, steps):
        at = self.selected()
        at = len(self.steps) if at is None else at + 1
        self.steps[at:at] = steps
        self.show(at + len(steps) - 1)

    def add_key(self):
        steps = KeyDialog(self.top).result
        if steps:
            self.insert(steps)

    def add_wait(self):
        from tkinter import simpledialog
        ms = simpledialog.askinteger(
            "Add a wait", "How long to wait, in milliseconds (1000 = 1 second):",
            parent=self.top, initialvalue=50, minvalue=1, maxvalue=MACRO_MAX_WAIT)
        if ms:
            self.insert([("wait", ms)])

    def move(self, by):
        at = self.selected()
        if at is None or not 0 <= at + by < len(self.steps):
            return
        self.steps[at], self.steps[at + by] = self.steps[at + by], self.steps[at]
        self.show(at + by)

    def remove(self):
        at = self.selected()
        if at is not None:
            del self.steps[at]
            self.show(at)

    def clear(self):
        self.steps = []
        self.show()

    # -- recording ---------------------------------------------------------

    def toggle_record(self):
        self.recording = not self.recording
        self.held.clear()
        self.last = None
        self.record_btn.configure(text="Stop" if self.recording else "Record keys")
        for button in self.edit_buttons:
            button.configure(state="disabled" if self.recording else "normal")
        self.record_hint.set(
            "Recording. Type the keys now, then click Stop. (The Windows key "
            "and some Alt keys cannot be recorded: add those with Add a key.)"
            if self.recording else
            "Record keys: click it, type the keys on your keyboard, then "
            "click Stop. The time between your key presses is recorded too.")
        if self.recording:
            # Keys must reach the recorder, not press whichever button has
            # the keyboard focus.
            self.list.focus_set()
        else:
            self.steps = mouse_win.tidy_steps(self.steps)
            self.show()

    def record(self, kind, event):
        name = VK_NAMES.get(event.keycode)
        if not name:
            return
        if self.last is not None:
            self.steps.append(("wait", max(1, min(MACRO_MAX_WAIT, event.time - self.last))))
        self.last = event.time
        self.steps.append((kind, name))
        self.show(len(self.steps) - 1)

    def key_down(self, event):
        if not self.recording:
            return None
        if event.keycode not in self.held:      # a held key repeats itself
            self.held.add(event.keycode)
            self.record("down", event)
        return "break"

    def key_up(self, event):
        if not self.recording:
            return None
        if event.keycode in self.held:
            self.held.discard(event.keycode)
            self.record("up", event)
        return "break"

    def ok(self):
        if self.recording:
            self.toggle_record()
        try:
            count = int(self.count.get()) if self.mode.get() == MACRO_TIMES else 1
        except ValueError:
            count = 0
        macro = {"name": self.name.get().strip()[:15] or "Macro", "mode": self.mode.get(),
                 "count": count, "steps": mouse_win.tidy_steps(self.steps)}
        try:
            mouse_win.check_macro(macro)
        except ValueError as e:
            messagebox.showwarning("Macro", str(e), parent=self.top)
            return
        down = set()
        for kind, key in macro["steps"]:
            if kind == "down":
                down.add(key)
            elif kind == "up":
                down.discard(key)
        if down and not messagebox.askyesno(
                "Macro", f"The macro presses {', '.join(sorted(down))} but never "
                "releases it. The PC will act as if you are still holding it.\n\n"
                "Keep the macro like this?", parent=self.top, default="no"):
            return
        self.result = macro
        self.top.destroy()


class Window:
    """The form edits a copy of the mouse's settings; `saved` is what the
    mouse holds. Nothing reaches the mouse until Apply, and Apply sends only
    what differs."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(DISPLAY_NAME)
        try:
            self.root.iconbitmap(default=ICON)
        except tk.TclError:
            pass
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.mouse = None
        self.saved = None           # what the mouse holds; None until read
        self.busy = False
        self.closing = threading.Event()
        self.listener = None
        self._loading = False       # pushing settings into the controls
        self.key_values = list(DEFAULTS["keys"])
        self.macros = [None] * len(KEYS)
        self.link = self.battery = ""
        self.level = None           # the last battery reading, in percent
        self.status_text = tk.StringVar(value="Looking for the mouse...")
        self.note_text = tk.StringVar(value="")
        self.inputs = []            # every control that edits a setting
        self._build()
        self._enable()
        threading.Thread(target=self._listen, name="mouse", daemon=True).start()
        self.root.after(50, self.load)

    # -- layout ------------------------------------------------------------

    def _build(self):
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Hint.TLabel", foreground=GREY)
        style.configure("Note.TLabel", foreground=AMBER)

        outer = ttk.Frame(self.root, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        ttk.Label(outer, textvariable=self.status_text).grid(
            row=0, column=0, sticky="w", pady=(0, 10))
        self.tabs = tabs = ttk.Notebook(outer)
        tabs.grid(row=1, column=0, sticky="nsew")
        for name, build in (("Sensor", self._build_sensor), ("DPI", self._build_dpi),
                            ("Buttons", self._build_buttons),
                            ("Options", self._build_options)):
            page = ttk.Frame(tabs, padding=14)
            tabs.add(page, text=name)
            build(page)

        ttk.Label(outer, textvariable=self.note_text, style="Note.TLabel",
                  wraplength=WRAP + 110).grid(row=2, column=0, sticky="w", pady=(10, 0))
        bar = ttk.Frame(outer)
        bar.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self.reset_btn = ttk.Button(bar, text="Reset to defaults", command=self.reset)
        self.reset_btn.pack(side="left")
        self.undo_btn = ttk.Button(bar, text="Undo changes", command=self.load)
        self.undo_btn.pack(side="left", padx=(6, 0))
        self.apply_btn = ttk.Button(bar, text="Apply", command=self.apply)
        self.apply_btn.pack(side="right")
        ttk.Label(bar, text=f"v{VERSION}", style="Hint.TLabel").pack(side="right", padx=10)

    def _var(self, kind, **options):
        var = kind(**options)
        var.trace_add("write", self._changed)
        return var

    def _row(self, page, row, text):
        ttk.Label(page, text=text).grid(row=row, column=0, sticky="nw",
                                        padx=(0, 14), pady=(8, 2))
        frame = ttk.Frame(page)
        frame.grid(row=row, column=1, sticky="w", pady=(8, 2))
        return frame

    def _about(self, page, row, text, column=1, span=1, indent=0):
        """An explanation under a control."""
        label = ttk.Label(page, text=text, style="Hint.TLabel", justify="left",
                          wraplength=WRAP - indent if span == 1 else WRAP + 110 - indent)
        label.grid(row=row, column=column, columnspan=span, sticky="w",
                   padx=(indent, 0))
        return label

    def _radios(self, frame, var, choices):
        made = []
        for value, text in choices:
            radio = ttk.Radiobutton(frame, text=text, variable=var, value=value)
            radio.pack(side="left", padx=(0, 10))
            made.append(radio)
        self.inputs += made
        return made

    def _build_sensor(self, page):
        self.rate = self._var(tk.StringVar)
        box = ttk.Combobox(self._row(page, 0, "Report rate"), textvariable=self.rate,
                           state="readonly", width=9,
                           values=[f"{hz} Hz" for hz in sorted(RATES)])
        box.pack(side="left")
        self.inputs.append(box)
        self._about(page, 1, ABOUT_RATE)

        self.lod = self._var(tk.IntVar)
        self._radios(self._row(page, 2, "Lift-off distance"), self.lod,
                     [(code, LODS[code]) for code in LOD_ORDER])
        self._about(page, 3, ABOUT_LOD)

        self.sensor_mode = self._var(tk.IntVar)
        self.mode_radios = self._radios(self._row(page, 4, "Sensor mode"),
                                        self.sensor_mode, list(enumerate(SENSOR_MODES)))
        self.mode_about = self._about(page, 5, ABOUT_MODE)

        self.motion_sync = self._var(tk.BooleanVar)
        self.angle_snap = self._var(tk.BooleanVar)
        self.ripple = self._var(tk.BooleanVar)
        for row, (var, text, about) in enumerate((
                (self.motion_sync, "Motion sync", ABOUT_SYNC),
                (self.angle_snap, "Angle snapping", ABOUT_SNAP),
                (self.ripple, "Ripple control", ABOUT_RIPPLE))):
            check = ttk.Checkbutton(page, text=text, variable=var)
            check.grid(row=6 + 2 * row, column=0, columnspan=2, sticky="w", pady=(10, 0))
            self.inputs.append(check)
            self._about(page, 7 + 2 * row, about, column=0, span=2, indent=20)

    def _build_dpi(self, page):
        self._about(page, 0, ABOUT_DPI, column=0, span=2)
        self.stages = self._var(tk.StringVar)
        spin = ttk.Spinbox(self._row(page, 1, "Stages in use"), textvariable=self.stages,
                           from_=1, to=STAGES, width=5, state="readonly")
        spin.pack(side="left")
        self.stages_spin = spin
        self._about(page, 2, ABOUT_STAGES)

        table = ttk.Frame(page)
        table.grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 4))
        ttk.Label(table, text="In use now", style="Hint.TLabel").grid(
            row=0, column=0, padx=(0, 14))
        ttk.Label(table, text="DPI", style="Hint.TLabel").grid(row=0, column=2, sticky="w")
        self.stage = self._var(tk.IntVar)
        self.dpi, self.stage_rows = [], []
        for i in range(STAGES):
            radio = ttk.Radiobutton(table, variable=self.stage, value=i)
            radio.grid(row=i + 1, column=0, padx=(0, 14), pady=2)
            ttk.Label(table, text=f"Stage {i + 1}").grid(row=i + 1, column=1,
                                                       sticky="w", padx=(0, 14))
            var = self._var(tk.StringVar)
            spin = ttk.Spinbox(table, textvariable=var, from_=DPI_MIN, to=DPI_MAX,
                               increment=DPI_STEP, width=8)
            spin.grid(row=i + 1, column=2, pady=2)
            self.dpi.append(var)
            self.stage_rows.append((radio, spin))
        self._about(page, 4, f"You can use {DPI_MIN} to {DPI_MAX}, in steps of "
                             f"{DPI_STEP}. Most people use 400 to 3200.",
                    column=0, span=2)

    def _build_buttons(self, page):
        self.keys = []
        names = [name for name, _ in FUNCTIONS] + [SHORTCUT, MACRO]
        for i, name in enumerate(KEYS[:ASSIGNABLE]):
            ttk.Label(page, text=name).grid(row=i, column=0, sticky="w",
                                            padx=(0, 14), pady=3)
            var = tk.StringVar()
            box = ttk.Combobox(page, textvariable=var, state="readonly", width=34,
                               values=names, height=16)
            box.grid(row=i, column=1, sticky="w", pady=3)
            box.bind("<<ComboboxSelected>>", lambda e, i=i: self._key_picked(i))
            self.keys.append(var)
            self.inputs.append(box)
        ttk.Label(page, text=KEYS[ASSIGNABLE]).grid(row=ASSIGNABLE, column=0, sticky="w",
                                                    padx=(0, 14), pady=3)
        self._about(page, ASSIGNABLE, ABOUT_DPI_BUTTON)
        self._about(page, ASSIGNABLE + 1, ABOUT_BUTTONS, column=0, span=2).grid(pady=(6, 0))

        self.fire_times = self._var(tk.StringVar)
        self.fire_speed = self._var(tk.StringVar)
        frame = self._row(page, ASSIGNABLE + 2, "Fire")
        for text, var, top in (("Clicks", self.fire_times, FIRE_TIMES_MAX),
                               ("Speed", self.fire_speed, FIRE_SPEED_MAX)):
            ttk.Label(frame, text=text).pack(side="left", padx=(0, 6))
            spin = ttk.Spinbox(frame, textvariable=var, from_=0, to=top, width=5)
            spin.pack(side="left", padx=(0, 16))
            self.inputs.append(spin)
        self._about(page, ASSIGNABLE + 3, ABOUT_FIRE)

        self.debounce = self._var(tk.StringVar)
        frame = self._row(page, ASSIGNABLE + 4, "Debounce")
        spin = ttk.Spinbox(frame, textvariable=self.debounce, from_=0,
                           to=DEBOUNCE_MAX, width=5)
        spin.pack(side="left")
        ttk.Label(frame, text="ms").pack(side="left", padx=(6, 0))
        self.inputs.append(spin)
        self._about(page, ASSIGNABLE + 5, ABOUT_DEBOUNCE)

    def _build_options(self, page):
        self.sleep = self._var(tk.StringVar)
        box = ttk.Combobox(self._row(page, 0, "Sleep after"), textvariable=self.sleep,
                           state="readonly", width=12, values=list(SLEEP_TEXTS))
        box.pack(side="left")
        self.inputs.append(box)
        self._about(page, 1, ABOUT_SLEEP)

        frame = self._row(page, 2, "Profile")
        self.export_btn = ttk.Button(frame, text="Save to a file...", command=self.export)
        self.export_btn.pack(side="left", padx=(0, 6))
        self.import_btn = ttk.Button(frame, text="Load from a file...", command=self.load_file)
        self.import_btn.pack(side="left")
        self._about(page, 3, ABOUT_PROFILE)

        self.autostart = tk.BooleanVar(value=autostart_on())
        ttk.Checkbutton(page, text="Show the battery icon when Windows starts",
                        variable=self.autostart, command=self._autostart).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))
        self._about(page, 5, ABOUT_AUTOSTART, column=0, span=2, indent=20)

    # -- the form ----------------------------------------------------------

    def key_text(self, i):
        """What the list of button `i` shows for what it is set to."""
        value = self.key_values[i]
        if mouse_win.is_macro(value) and self.macros[i]:
            return f"Macro: {self.macros[i]['name']}"
        return mouse_win.describe_key(value)

    def fill(self, s):
        """Show settings `s` in the controls."""
        self._loading = True
        self.rate.set(f"{s['rate']} Hz")
        self.lod.set(s["lod"])
        self.sensor_mode.set(s["sensor_mode"])
        self.motion_sync.set(s["motion_sync"])
        self.angle_snap.set(s["angle_snap"])
        self.ripple.set(s["ripple"])
        self.debounce.set(str(s["debounce"]))
        self.sleep.set(sleep_text(s["sleep"]))
        self.stages.set(str(s["stages"]))
        self.stage.set(s["stage"])
        self.fire_times.set(str(s["fire_times"]))
        self.fire_speed.set(str(s["fire_speed"]))
        for var, dpi in zip(self.dpi, s["dpi"]):
            var.set(str(dpi))
        self.key_values = list(s["keys"])
        self.macros = list(s["macros"])
        for i, var in enumerate(self.keys):
            var.set(self.key_text(i))
        self._loading = False
        self._enable()

    def collect(self):
        """The settings the controls show. ValueError if one can't be read."""
        try:
            numbers = [int(v.get()) for v in (self.debounce, self.stages, self.fire_times,
                                              self.fire_speed, *self.dpi)]
        except ValueError:
            raise ValueError("Debounce, Fire and DPI must be whole numbers.") from None
        return {
            "rate": int(self.rate.get().split()[0]),
            "lod": self.lod.get(), "sensor_mode": self.sensor_mode.get(),
            "ripple": self.ripple.get(), "angle_snap": self.angle_snap.get(),
            "motion_sync": self.motion_sync.get(),
            "debounce": numbers[0], "sleep": SLEEP_TEXTS[self.sleep.get()],
            "stages": numbers[1], "stage": self.stage.get(), "dpi": numbers[4:],
            "dpi_light": self.saved["dpi_light"], "dpi_extra": self.saved["dpi_extra"],
            "fire_times": numbers[2], "fire_speed": numbers[3],
            "keys": list(self.key_values),
            # A macro only counts while its button is set to play it.
            "macros": [m if mouse_win.is_macro(v) else None
                       for m, v in zip(self.macros, self.key_values)],
        }

    def dirty(self):
        """True when the form no longer shows what the mouse holds."""
        try:
            return self.collect() != self.saved
        except ValueError:
            return True

    def _changed(self, *_):
        if not self._loading and self.saved is not None:
            # Switching a stage off must not leave it as the one in use.
            if self.stages.get().isdigit():
                top = int(self.stages.get()) - 1
                if self.stage.get() > top:
                    self.stage.set(top)
                    return
            self._enable()

    def _enable(self):
        """Switch every control on or off to fit the state of things."""
        ready = self.saved is not None and not self.busy
        on = "normal" if ready else "disabled"
        for widget in self.inputs:
            widget.configure(state="readonly" if ready and isinstance(
                widget, ttk.Combobox) else on)
        self.stages_spin.configure(state="readonly" if ready else "disabled")
        stages = int(self.stages.get()) if self.stages.get().isdigit() else STAGES
        for i, (radio, spin) in enumerate(self.stage_rows):
            radio.configure(state=on if i < stages else "disabled")
            spin.configure(state=on)
        fast = ready and int(self.rate.get().split()[0]) > SENSOR_MODE_MAX_RATE
        for radio in self.mode_radios:
            radio.configure(state="disabled" if fast or not ready else "normal")
        self.mode_about.configure(text=ABOUT_MODE_FAST if fast else ABOUT_MODE)
        changed = ready and self.dirty()
        self.apply_btn.configure(state="normal" if changed else "disabled")
        self.undo_btn.configure(state="normal" if changed else "disabled")
        for button in (self.reset_btn, self.export_btn, self.import_btn):
            button.configure(state=on)

    def _key_picked(self, i):
        name = self.keys[i].get()
        if name == SHORTCUT:
            value = ShortcutDialog(self.root, self.key_values[i]).result
            if value is not None:
                self.key_values[i] = value
        elif name == MACRO:
            macro = MacroDialog(self.root, KEYS[i], self.macros[i]).result
            if macro is not None:
                self.macros[i] = macro
                self.key_values[i] = mouse_win.macro_key(i)
        elif name in dict(FUNCTIONS):
            self.key_values[i] = dict(FUNCTIONS)[name]
        self.keys[i].set(self.key_text(i))
        self._enable()

    # -- the mouse ---------------------------------------------------------

    def background(self, work, done):
        """Run `work` off the UI thread; call done(result, error) back on it."""
        def run():
            try:
                result, error = work(), None
            except Exception as e:
                result, error = None, e
            self._post(lambda: done(result, error))
        threading.Thread(target=run, daemon=True).start()

    def _post(self, call):
        if not self.closing.is_set():
            try:
                self.root.after(0, call)
            except (tk.TclError, RuntimeError):
                pass                    # the window closed meanwhile

    def _status(self):
        self.status_text.set("   ·   ".join(t for t in (self.link, self.battery) if t)
                             or "Looking for the mouse...")

    def _begin(self, note):
        self.busy = True
        self.note_text.set(note)
        self._enable()

    def _failed(self, error):
        """The mouse did not do as asked: say why, and start afresh."""
        if self.mouse:
            self.mouse.close()
            self.mouse = None
        self.saved = None
        self.link = ""
        self._status()
        self.note_text.set(str(error))
        self._enable()

    def load(self):
        """Read the mouse and show what it holds, dropping unapplied changes."""
        if self.busy:
            return
        self._begin("Reading the mouse...")

        def work():
            if self.mouse is None:
                self.mouse = mouse_win.Mouse()
            return mouse_win.read_settings(self.mouse)

        def done(settings, error):
            self.busy = False
            if error:
                self._failed(error)
                return
            self.saved = settings
            self.link = ("Nova X21 connected (" +
                         ("cable" if self.mouse.link == "cable" else "wireless receiver") + ")")
            self._status()
            self.note_text.set("")
            self.fill(settings)

        self.background(work, done)

    def apply(self):
        try:
            new = self.collect()
            mouse_win.check(new)
        except ValueError as e:
            messagebox.showwarning(DISPLAY_NAME, str(e), parent=self.root)
            return
        old = self.saved
        self._begin("Sending to the mouse...")

        def work():
            mouse_win.apply(
                self.mouse, old, new,
                step=lambda what: self._post(
                    lambda: self.note_text.set(f"Sending to the mouse: {what}...")))
            return mouse_win.read_settings(self.mouse)

        def done(settings, error):
            self.busy = False
            if error:
                self._failed(error)
                return
            self.saved = settings
            self.note_text.set("Done. The mouse has the new settings." if settings == new
                               else "The mouse changed some of this itself. The "
                                    "window now shows what the mouse has.")
            self.fill(settings)

        self.background(work, done)

    def reset(self):
        keys = list(DEFAULTS["keys"])
        keys[ASSIGNABLE:] = self.saved["keys"][ASSIGNABLE:]
        self.fill({**DEFAULTS, "keys": keys, "dpi_light": self.saved["dpi_light"],
                   "dpi_extra": self.saved["dpi_extra"]})
        self.note_text.set("These are the settings the mouse came with. Click "
                           "Apply to send them to the mouse.")

    def export(self):
        try:
            settings = self.collect()
            mouse_win.check(settings)
        except ValueError as e:
            messagebox.showwarning(DISPLAY_NAME, str(e), parent=self.root)
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Save the profile", defaultextension=".json",
            initialfile="Nova X21 profile.json",
            filetypes=[("Nova X21 profile", "*.json")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(mouse_win.profile_text(settings))
        except OSError as e:
            messagebox.showerror(DISPLAY_NAME, f"Could not save the file:\n\n{e}",
                                 parent=self.root)
            return
        self.note_text.set(f"Saved to {os.path.basename(path)}.")

    def load_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self.root, title="Load a profile",
            filetypes=[("Nova X21 profile", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                settings = mouse_win.profile_settings(f.read(2_000_000), self.saved)
        except (OSError, UnicodeError) as e:
            messagebox.showerror(DISPLAY_NAME, f"Could not read the file:\n\n{e}",
                                 parent=self.root)
            return
        except ValueError as e:
            messagebox.showwarning(DISPLAY_NAME, str(e), parent=self.root)
            return
        self.fill(settings)
        self.note_text.set(f"Loaded {os.path.basename(path)}. Click Apply to "
                           "send it to the mouse.")

    def _autostart(self):
        try:
            set_autostart(self.autostart.get())
        except OSError as e:
            self.autostart.set(autostart_on())
            messagebox.showerror(DISPLAY_NAME, f"Could not change that:\n\n{e}",
                                 parent=self.root)

    # -- what the mouse says by itself -------------------------------------

    def _listen(self):
        while not self.closing.is_set():
            try:
                self.listener = mouse_win.Listener()
            except MouseError as e:
                self._post(lambda e=e: self._heard_nothing(str(e)))
                self.closing.wait(3)
                continue
            try:
                asleep = False
                while True:
                    status = self.listener.wait()
                    if status is None:
                        # Quiet for a while. That is a sleeping mouse, or one
                        # being moved: it only reports while it lies still.
                        # One question settles it (it is not asked while the
                        # window itself is talking to the mouse).
                        if not asleep and mouse_win.awake() is False:
                            asleep = True
                            self._post(lambda: self._heard(None))
                        continue
                    asleep = False
                    self._post(lambda s=status: self._heard(s))
            except MouseError:
                pass
            finally:
                self.listener.close()
                self.listener = None

    def _heard_nothing(self, why):
        self.battery = ""
        if self.saved is None and not self.busy:
            self.note_text.set(why)
        self._status()

    def _heard(self, status):
        if status is None:
            # Only said once the mouse was asked and did not answer.
            was = f" (battery was {self.level}%)" if self.level is not None else ""
            self.battery = f"The mouse is asleep or switched off{was}"
            self._status()
            return
        self.level = status.battery
        self.battery = (f"Battery {status.battery}%"
                        f"{', charging' if status.charging else ''}")
        self._status()
        if self.busy:
            return
        if self.saved is None:
            self.load()                 # it woke up: read it now
        elif status.stage != self.saved["stage"] and status.stage < self.saved["stages"]:
            # The DPI button was pressed. Follow it, unless the form has a
            # stage of its own waiting to be applied.
            follow = self.stage.get() == self.saved["stage"]
            self.saved["stage"] = status.stage
            if follow:
                self._loading = True
                self.stage.set(status.stage)
                self._loading = False
            self._enable()

    def close(self):
        self.closing.set()
        if self.listener:
            self.listener.stop()
        if self.mouse and not self.busy:
            self.mouse.close()
        self.root.destroy()


def main():
    # One window. A second launch brings the first to the front.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32")
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    mutex = kernel32.CreateMutexW(None, False, MUTEX)
    if ctypes.get_last_error() == 183:      # ERROR_ALREADY_EXISTS
        open_window = user32.FindWindowW("TkTopLevel", DISPLAY_NAME)
        if open_window:
            user32.ShowWindow(open_window, 9)       # restore if minimised
            user32.SetForegroundWindow(open_window)
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # crisp text on high-DPI screens
    except (AttributeError, OSError):
        pass
    Window().root.mainloop()
    del mutex


if __name__ == "__main__":
    main()
