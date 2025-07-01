#define MyAppName "zerokey"
#define MyAppVersion "1.2.2"
#define MyAppPublisher "ysAlex"
#define MyAppURL "https://github.com/ysalexg/zerokey"
#define MyAppExeName "zerokey.exe"

[Setup]
AppId={{AEAEA68F-06AE-43D7-B17C-367CB8F6F7DA}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=D:\Programacion\Python\zerokey\compiler
OutputBaseFilename=zerokeyInstaller
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked
Name: "autostart_service"; Description: "Iniciar servicio de Zerokey con Windows"; Flags: checkedonce

[Files]
Source: "D:\\Programacion\\Python\\zerokey\\compiler\\releases\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\zerokey service"; Filename: "{app}\zerokeyService.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Run"; ValueType: string; ValueName: "ZerokeyService"; ValueData: """{app}\\zerokeyService.exe"""; Flags: uninsdeletevalue; Tasks: autostart_service

[Run]
Filename: "{app}\zerokeyService.exe"; Description: "Ejecutar servicio de Zerokey"; Flags: postinstall unchecked nowait

[Code]
var
  ConfigLines: TStringList;
  PageDownload, PageGame: TInputDirWizardPage;
  PageOptions: TWizardPage;
  CheckAchievements, CheckDeleteFiles: TNewCheckBox;
  StrAchievements, StrDelete: String;

procedure InitializeWizard;
begin
  // Página para carpeta de descargas
  PageDownload := CreateInputDirPage(
    wpSelectDir,
    'Carpeta de descargas',
    'Elija la carpeta donde se leeran las descargas.',
    'Debe ser la misma que en Hydra.',
    False, '');
  PageDownload.Add('Descargas:');
  PageDownload.Values[0] := ExpandConstant('{userdocs}\Downloads');

  // Página para carpeta de juegos
  PageGame := CreateInputDirPage(
    PageDownload.ID,
    'Carpeta de juegos',
    'Elija la carpeta donde se instalaran los juegos.',
    'Ruta donde Zerokey instalará los juegos.',
    False, '');
  PageGame.Add('Juegos:');
  PageGame.Values[0] := ExpandConstant('{userdocs}\Games');

  // Página de opciones adicionales
  PageOptions := CreateCustomPage(
    PageGame.ID,
    'Opciones adicionales',
    'Configure opciones adicionales:');

  CheckAchievements := TNewCheckBox.Create(PageOptions);
  CheckAchievements.Parent := PageOptions.Surface;
  CheckAchievements.Caption := 'Habilitar logros';
  CheckAchievements.Top := ScaleY(8);
  CheckAchievements.Left := ScaleX(0);
  CheckAchievements.Checked := True;

  CheckDeleteFiles := TNewCheckBox.Create(PageOptions);
  CheckDeleteFiles.Parent := PageOptions.Surface;
  CheckDeleteFiles.Caption := 'Eliminar archivos después de extraer';
  CheckDeleteFiles.Top := CheckAchievements.Top + CheckAchievements.Height + ScaleY(8);
  CheckDeleteFiles.Left := ScaleX(0);
  CheckDeleteFiles.Checked := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Convertir booleanos a 'true'/'false'
    if CheckAchievements.Checked then
      StrAchievements := 'true'
    else
      StrAchievements := 'false';

    if CheckDeleteFiles.Checked then
      StrDelete := 'true'
    else
      StrDelete := 'false';

    // Crear y llenar archivo config.yaml
    ConfigLines := TStringList.Create;
    try
      ConfigLines.Add('paths:');
      ConfigLines.Add('  download_folder: ''' + PageDownload.Values[0] + '''');
      ConfigLines.Add('  game_folder: ''' + PageGame.Values[0] + '''');
      ConfigLines.Add('  excluded_folders:');
      ConfigLines.Add('    - ''E:\Descargas\TempDownload''');
      ConfigLines.Add('achievements: ' + StrAchievements);
      ConfigLines.Add('extraction: true');
      ConfigLines.Add('delete_files: ' + StrDelete);
      ConfigLines.Add('show_tray: true');
      ConfigLines.SaveToFile(ExpandConstant('{app}\config.yaml'));
    finally
      ConfigLines.Free;
    end;
  end;
end;

