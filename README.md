# CrystalX Nova X21 for Windows

See the battery of your **CrystalX Nova X21 Red** mouse next to the clock, and
change every setting of the mouse — report rate, DPI, buttons, macros and
more — without the vendor's NOVA X21 Red app.

The mouse keeps its settings inside itself. So this app does not have to stay
open: set the mouse up, close the app, and the mouse works the same. Open the
app again only when you want to see the battery or change something.

This is an unofficial project. It is not made by or connected with CrystalX.

- [Install](#install)
- [Using the app](#using-the-app)
- [Good to know](#good-to-know)
- [Update or uninstall](#update-or-uninstall)
- [If something goes wrong](#if-something-goes-wrong)
- [Run it without installing, or build it yourself](#run-it-without-installing-or-build-it-yourself)
- [How it works](#how-it-works)
- [License](#license)

---

## Install

**You need:** the CrystalX Nova X21 Red mouse with its wireless receiver
plugged into the PC, and Windows 10 or 11, 64-bit. Nothing else — the
installer contains everything.

1. **Close the vendor's NOVA X21 Red app** if it is running. Two programs
   cannot talk to the mouse at the same time.

2. **Download the installer.** Open the
   **[latest release](https://github.com/Abdul-Moez/CrystalX-Nova-X21-Red-Software-For-Windows/releases/latest)**
   and click **`CrystalX-Nova-X21-Setup-<version>.exe`** under *Assets*.

3. **Run it.** Windows may say **"Windows protected your PC"** — the installer
   is not code-signed, so Windows does not know who made it. Click **More
   info**, then **Run anyway**.

4. **Click through the steps:**
   - the license (GPL v3) — click **I accept** and **Next**;
   - two boxes you can tick if you want them: a shortcut on the desktop, and
     showing the battery icon every time Windows starts;
   - **Install**, then **Finish** (with *Open CrystalX Nova X21* ticked).

The battery icon appears next to the clock and the settings window opens.

Windows does **not** ask for an administrator. The app is installed for your
user only, and it installs no service and no driver.

**What the installer puts on your PC**, so nothing is a surprise:

| What | Why |
|---|---|
| The app, in `%LOCALAPPDATA%\Programs\CrystalX Nova X21` | The program itself |
| A Start menu entry, **CrystalX Nova X21** | Opens the app |
| A desktop shortcut | Only if you ticked that box |
| The battery icon at every login | Only if you ticked that box. You can change it later in the app |

---

## Using the app

Open **CrystalX Nova X21** from the Start menu.

### The battery icon

A small icon next to the clock shows the battery as a number. Windows may hide
a new icon behind the **^** arrow; you can drag it out to keep it in view.

| The icon | It means |
|---|---|
| Green number | 50% or more |
| Orange number | 20% to 49% |
| Red number | Below 20% — charge the mouse soon |
| Blue number | The mouse is charging |
| Grey number | The mouse is asleep or switched off. The number is the last one it reported |
| Grey **?** | The app is waiting for the mouse to report |
| Grey **-** | The receiver is not plugged in |

**Click** the icon to open the settings window. **Right-click** it for
**Show** and **Quit**. Quit closes the app completely; the mouse keeps working.

The icon costs almost nothing while it sits there. It does not keep asking the
mouse for the battery: the mouse reports it by itself, and the app only
listens.

### The settings window

The window shows what the mouse has now. Change what you like, then click
**Apply** to send it to the mouse. Nothing reaches the mouse before you click
Apply. Under every setting there is a short text that says what it does and
what it can cause.

- **Sensor**
  - **Report rate** — 125 to 8000 Hz.
  - **Lift-off distance** — 0.7, 1 or 2 mm.
  - **Sensor mode** — low power, high performance or corded.
  - **Motion sync**, **angle snapping** and **ripple control**.
- **DPI**
  - How many DPI stages the DPI button goes through, from 1 to 6.
  - The DPI of each stage, from 50 to 26000.
  - Which stage is in use now. This follows the mouse when you press its DPI
    button.
- **Buttons** — what the left, right, wheel, back and forward buttons do:
  - a mouse click, back or forward;
  - **Fire**: fast clicks while you hold the button, with settings for how
    many clicks and how fast;
  - DPI up, DPI down or DPI loop;
  - media keys (play, next, volume, mute…), apps (calculator, email, File
    Explorer…) and browser keys;
  - a **keyboard shortcut**, for example Ctrl + C;
  - a **macro**: a list of key presses that the mouse plays. You can record it
    from your keyboard or build it step by step, and choose if it plays once,
    several times, while you hold the button, or until you press the button
    again;
  - **Disabled**.

  This tab also has **Debounce**: how long the mouse waits before it accepts
  the next click.
- **Options**
  - **Sleep after** — how long the mouse waits before it goes to sleep.
  - **Profile** — save every setting to a file, or load them from a file.
  - **Show the battery icon when Windows starts.**

**Undo changes** puts the window back to what the mouse has now.
**Reset to defaults** fills in the settings the mouse came with; click Apply
to send them.

**Closing the window** with **X** only closes the window. The battery icon
stays until you choose Quit.

---

## Good to know

- **The mouse sleeps.** When you do not touch it for a while, it goes to sleep
  to save battery, and then it cannot answer the app. Move it or click it to
  wake it up.
- **Macros and settings live in the mouse.** They keep working when the app is
  closed, and on another PC.
- **One button always stays as Left click.** The app refuses to remove the
  last one, because without it you could not click anything.
- **The DPI button cannot be changed.** The vendor's app does not change it
  either.
- **A macro holds up to 70 key steps.** Each press and each release is one
  step. Waits between them are free.
- **Some online games do not allow macros or Fire.** Check the rules of your
  game.
- **Made and tested with the wireless receiver.** With the cable the app
  should work the same way, but that has not been tested.
- **Not included:** the vendor's five profile slots that a button can switch
  between. They only work while the vendor's app is running, and this app is
  built so that the mouse never needs it. Use profile files instead. This app
  also cannot read the vendor's own profile files.

---

## Update or uninstall

**To update:** download the newer `CrystalX-Nova-X21-Setup-<version>.exe` from
the
[releases page](https://github.com/Abdul-Moez/CrystalX-Nova-X21-Red-Software-For-Windows/releases)
and run it. The mouse keeps its settings.

**To uninstall:** open **Settings → Apps**, find **CrystalX Nova X21** and
click **Uninstall**. This removes the app, the Start menu entry, the desktop
shortcut and the icon at login. The mouse keeps its settings. Profile files
you saved stay where you saved them.

---

## If something goes wrong

**"The mouse's receiver is not plugged in."**
Windows cannot see the receiver. Plug it in, or try another USB port. The app
notices by itself when it is back.

**"The mouse is not answering. Move it to wake it up, and check it is switched on."**
The mouse is asleep, switched off, or too far away. Move it or click it. Check
the switch under the mouse, and charge it if the battery may be empty.

**"The mouse did not take the new …", or a setting that will not stay**
Close the vendor's NOVA X21 Red app, and look for its icon next to the clock
too. Two programs cannot talk to the mouse at the same time. Then click Apply
again.

**"Another program is talking to the mouse. Close it and try again."**
Another copy of this app, or its command-line tool, is busy with the mouse.
Wait a moment, or close it.

**"At least one button must stay set to Left click."**
Give one button the Left click before you click Apply.

**The icon shows a grey number**
The mouse is asleep or switched off. The number is the last battery level it
reported. It turns back to a colour when you move the mouse.

**The battery number does not change for a while**
The mouse only reports its battery while it lies still. While you move it,
the icon keeps the last number.

**I cannot find the icon next to the clock**
Click the **^** arrow next to the icons; Windows hides new icons there at
first. You can drag it out to keep it in view. Or open **CrystalX Nova X21**
from the Start menu.

**"Windows protected your PC" when running the installer**
Expected: the installer is not code-signed. Click **More info**, then **Run
anyway**. To be sure the file is the real one, compare its checksum with the
one on the release page — in PowerShell:
`Get-FileHash CrystalX-Nova-X21-Setup-<version>.exe`.

**Anything else**
[Report an issue](https://github.com/Abdul-Moez/CrystalX-Nova-X21-Red-Software-For-Windows/issues)
and say what you did and what the app showed.

---

## Run it without installing, or build it yourself

The app is three Python files and needs no extra libraries.

**Run it from the source files.** Install Python 3.10 or newer from
[python.org](https://www.python.org/downloads/windows/), download this
project, and double-click **`run.cmd`**. It shows the battery icon and opens
the settings window.

**Use it from the command line:**

```
python mouse_win.py                     show every setting and the battery
python mouse_win.py --watch             show what the mouse reports, as it comes
python mouse_win.py --export my.json    save every setting to a profile file
python mouse_win.py --import my.json    send a profile file to the mouse
python mouse_win.py --set debounce=10   change a setting
```

**Build the installer yourself.** Run **`packaging\build.cmd`**. It makes
`dist\CrystalX Nova X21\CrystalXNova.exe` and
`dist\CrystalX-Nova-X21-Setup-<version>.exe`. The build tools are downloaded
into folders of the project; nothing is installed on your PC. Use any Python
from 3.10 on **except 3.13.0**, which has a bug that breaks the build. If your
good Python is not the default one, give its path:
`packaging\build.cmd "C:\path\to\python.exe"`.

**Make a release** (for the maintainer). Change `VERSION` in `mouse_win.py`,
commit, then push a tag with the same number:

```
git tag v1.0.0
git push origin v1.0.0
```

GitHub then builds the installer and publishes it as a release (see
`.github/workflows/release.yml`). The tag and `VERSION` must match.

---

## How it works

- The receiver is a USB device (`093A:522C`) that shows up as several HID
  devices. One of them, with usage page `FF05`, carries the settings.
- Every request is a small HID *feature report*, and the mouse answers the
  same way. Windows' own driver does all of it, so the app needs no driver, no
  extra library and no administrator rights.
- The mouse reports its battery by itself every two seconds while it lies
  still. The app listens for that, so it does not have to ask.
- A macro is 320 bytes, sent to the mouse in ten pieces and stored there.
- Every change is read back from the mouse after it is sent, so the app knows
  the mouse really took it.

The protocol was worked out by reading how the vendor's app talks to the
mouse. The details are written at the top of
[mouse_win.py](mouse_win.py) and next to the code that uses them.

| File | Purpose |
|---|---|
| `mouse_win.py` | Talks to the mouse: reads and writes every setting, macros, profile files. Also the command-line tool |
| `tray_win.py` | The battery icon next to the clock |
| `window_win.py` | The settings window |
| `run.cmd` | Starts the app from the source files |
| `assets/` | The app icon and the script that draws it |
| `packaging/` | Everything for building the exe and the installer |
| `.github/workflows/release.yml` | Builds the installer and publishes the release when a version tag is pushed |

---

## License

Copyright © 2026 **Abdul Moez** — [github.com/Abdul-Moez](https://github.com/Abdul-Moez)

This project is free software under the
**[GNU General Public License v3.0](LICENSE)** (or any later version).

In plain words — you may use, copy, change and share it, including for
commercial purposes, as long as:

- **you credit the original author** — keep the name and GitHub link above in
  every copy and modified version (an additional term under section 7(b) of
  the license, stated at the top of each code file);
- **you share your changes under GPL-3.0 as well**, with their source code, if
  you distribute a modified version;
- you keep the license and copyright notices intact.

The [LICENSE](LICENSE) file is the legally binding text; this summary is only a
guide.
