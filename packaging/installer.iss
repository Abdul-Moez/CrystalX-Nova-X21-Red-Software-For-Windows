; CrystalX Nova X21 mouse for Windows
; Copyright (C) 2026 Abdul Moez (https://github.com/Abdul-Moez)
; SPDX-License-Identifier: GPL-3.0-or-later -- see the LICENSE file.
;
; Inno Setup script for CrystalX-Nova-X21-Setup-<version>.exe. Built by
; packaging\build.cmd; by hand, after the PyInstaller build:
;
;   ISCC.exe /DAppVersion=1.0.0 packaging\installer.iss
;
; What it does:
;   install    copies the app into the user's own programs folder and adds
;              the Start menu entry. No admin rights, no service, no driver:
;              the mouse keeps its own settings and needs none of this.
;   upgrade    the same, over the old version
;   uninstall  removes all of that, and the "start with Windows" entry if the
;              app's own switch made one. The mouse keeps its settings.

#ifndef AppVersion
  #error Pass the version: ISCC /DAppVersion=1.0.0 ...
#endif
#ifndef DistDir
  #define DistDir "..\dist\CrystalX Nova X21"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

#define AppName "CrystalX Nova X21"
#define AppExe "CrystalXNova.exe"
#define RunKey "Software\Microsoft\Windows\CurrentVersion\Run"

[Setup]
; Never change AppId: Windows uses it to recognise upgrades of this app.
AppId={{6B0E4C1D-93A5-4F27-8E1B-2D7C5A9F4310}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Abdul Moez
AppPublisherURL=https://github.com/Abdul-Moez
; For this user only, so Windows never asks for an administrator.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
SetupIconFile=..\assets\crystalx-nova.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename=CrystalX-Nova-X21-Setup-{#AppVersion}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; The app is closed by PrepareToInstall below.
CloseApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Abdul Moez
VersionInfoDescription={#AppName} setup
VersionInfoCopyright=Copyright (C) 2026 Abdul Moez. GPL-3.0-or-later.
VersionInfoProductName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Put a shortcut on the desktop"; Flags: unchecked
Name: "autostart"; \
  Description: "Show the battery icon when Windows starts (you can change this later in the app)"; \
  Flags: unchecked

[InstallDelete]
; An upgrade replaces the bundled runtime completely rather than leaving old
; files next to new ones.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; \
  Comment: "Battery and settings of the CrystalX Nova X21 mouse"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; The same entry the app's own "start with Windows" switch writes, so the
; switch shows it as on. Left alone when the box is not ticked: the user may
; have switched it on in the app.
Root: HKCU; Subkey: "{#RunKey}"; ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExe}"" --hidden"; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "Open {#AppName}"; \
  Flags: postinstall nowait skipifsilent

[Code]
{ Close the icon and the window, so their files can be replaced or removed. }
procedure StopApp;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im {#AppExe}', '', SW_HIDE,
       ewWaitUntilTerminated, Code);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopApp;
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    StopApp;
    { Whether Setup or the app's own switch wrote it. }
    RegDeleteValue(HKCU, '{#RunKey}', '{#AppName}');
  end;
end;
