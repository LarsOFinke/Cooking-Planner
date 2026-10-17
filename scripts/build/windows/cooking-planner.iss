#ifndef AppVersion
  #error AppVersion must be passed from pyproject.toml with /DAppVersion
#endif

[Setup]
AppId={{ADBB9DA0-3D45-49BA-92E9-0B5C35B61C16}
AppName=Cooking Planner
AppVersion={#AppVersion}
AppPublisher=Cooking Planner
DefaultDirName={localappdata}\Programs\CookingPlanner
DefaultGroupName=Cooking Planner
PrivilegesRequired=lowest
OutputDir=..\..\..\dist\windows
OutputBaseFilename=CookingPlanner-Setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\CookingPlanner.exe

[Files]
Source: "..\..\..\dist\windows\CookingPlanner\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Cooking Planner"; Filename: "{app}\CookingPlanner.exe"
Name: "{autodesktop}\Cooking Planner"; Filename: "{app}\CookingPlanner.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\CookingPlanner.exe"; Description: "Launch Cooking Planner"; Flags: nowait postinstall skipifsilent
