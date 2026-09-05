; Inno Setup Script for DuoPad Windows Installer
#define MyAppName "DuoPad"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DuoPad Gaming"
#define MyAppURL "https://duopad.surge.sh"
#define MyAppExeName "DuoPad.exe"

[Setup]
AppId={{D37F8E3B-A94D-4E90-B8A2-7B4F558C3601}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\duopad-web
OutputBaseFilename=DuoPad_Setup
SetupIconFile=duopad_neon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\duopad_neon.ico
VersionInfoVersion=1.0.0.0
VersionInfoCompany=DuoPad Gaming
VersionInfoDescription=DuoPad Virtual Xbox 360 Gamepad Setup
VersionInfoCopyright=Copyright (C) 2026 DuoPad Open Source Project
VersionInfoProductName=DuoPad
VersionInfoProductVersion=1.0.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "duopad_neon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "duopad_icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "driver\ViGEmBusSetup_x64.msi"; DestDir: "{app}\driver"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\duopad_neon.ico"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\duopad_neon.ico"; Tasks: desktopicon

[Run]
Filename: "msiexec.exe"; Parameters: "/i ""{app}\driver\ViGEmBusSetup_x64.msi"" /passive /norestart"; Check: NeedsViGEmBus; Description: "Install Virtual Xbox Controller Driver (ViGEmBus)"; Flags: postinstall runascurrentuser
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsViGEmBus(): Boolean;
begin
  Result := not RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\ViGEmBus');
end;
