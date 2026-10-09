#define AppVersion "0.2.1"

[Setup]
#ifdef TestMode
AppId={{69C23A51-2744-48E0-9966-02F3CE16E601}
#else
AppId={{9E81C3D8-0F3D-4D2E-A612-60AEB63C8C0C}
#endif
AppName=Smart PDF
AppVersion={#AppVersion}
AppPublisher=Smart PDF contributors
AppPublisherURL=https://github.com/szymongazinski/smart-pdf
DefaultDirName={localappdata}\Programs\Smart PDF
DefaultGroupName=Smart PDF
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
OutputDir=..\dist\installer
#ifdef UpdateOnly
OutputBaseFilename=SmartPDF-Update-{#AppVersion}-x64
DisableWelcomePage=yes
DisableDirPage=yes
DisableReadyPage=yes
#else
OutputBaseFilename=SmartPDF-Setup-{#AppVersion}-x64
LicenseFile=..\LICENSE
#endif
SetupIconFile=..\assets\smart-pdf.ico
UninstallDisplayIcon={app}\SmartPDF.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
UninstallDisplayName=Smart PDF
VersionInfoDescription=Smart PDF Installer

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Skróty:"; Flags: unchecked
Name: "pdfopenwith"; Description: "Dodaj Smart PDF do menu Otwórz za pomocą dla plików PDF"; GroupDescription: "Integracja z systemem Windows:"; Flags: checkedonce
Name: "projectassociation"; Description: "Otwieraj projekty .smartpdf w Smart PDF"; GroupDescription: "Integracja z systemem Windows:"; Flags: checkedonce

[Files]
Source: "..\dist\SmartPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
#ifdef TestMode
Name: "{autoprograms}\Smart PDF Update Test"; Filename: "{app}\SmartPDF.exe"
Name: "{autodesktop}\Smart PDF Update Test"; Filename: "{app}\SmartPDF.exe"; Tasks: desktopicon
#else
Name: "{autoprograms}\Smart PDF"; Filename: "{app}\SmartPDF.exe"
Name: "{autodesktop}\Smart PDF"; Filename: "{app}\SmartPDF.exe"; Tasks: desktopicon
#endif

[Registry]
Root: HKCU; Subkey: "Software\Classes\Applications\SmartPDF.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "Smart PDF"; Flags: uninsdeletekey; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\Applications\SmartPDF.exe\shell\open\command"; ValueType: string; ValueData: """{app}\SmartPDF.exe"" ""%1"""; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\Applications\SmartPDF.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithList\SmartPDF.exe"; Flags: uninsdeletekey; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "SmartPDF.PDF"; ValueData: ""; Flags: uninsdeletevalue; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\SmartPDF.PDF"; ValueType: string; ValueData: "PDF document"; Flags: uninsdeletekey; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\SmartPDF.PDF\DefaultIcon"; ValueType: string; ValueData: "{app}\SmartPDF.exe,0"; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\SmartPDF.PDF\shell\open\command"; ValueType: string; ValueData: """{app}\SmartPDF.exe"" ""%1"""; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\Classes\.smartpdf"; ValueType: string; ValueData: "SmartPDF.Project"; Flags: uninsdeletevalue; Tasks: projectassociation
Root: HKCU; Subkey: "Software\Classes\SmartPDF.Project"; ValueType: string; ValueData: "Projekt Smart PDF"; Flags: uninsdeletekey; Tasks: projectassociation
Root: HKCU; Subkey: "Software\Classes\SmartPDF.Project\DefaultIcon"; ValueType: string; ValueData: "{app}\SmartPDF.exe,0"; Tasks: projectassociation
Root: HKCU; Subkey: "Software\Classes\SmartPDF.Project\shell\open\command"; ValueType: string; ValueData: """{app}\SmartPDF.exe"" ""%1"""; Tasks: projectassociation
Root: HKCU; Subkey: "Software\SmartPDF\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "Smart PDF"; Flags: uninsdeletekey; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\SmartPDF\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Lokalny edytor PDF z OCR"; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\SmartPDF\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "SmartPDF.PDF"; Tasks: pdfopenwith
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "Smart PDF"; ValueData: "Software\SmartPDF\Capabilities"; Flags: uninsdeletevalue; Tasks: pdfopenwith

[Run]
Filename: "{app}\SmartPDF.exe"; Description: "Uruchom Smart PDF"; Flags: nowait postinstall skipifsilent

#ifdef UpdateOnly
[Code]
function InitializeSetup(): Boolean;
var
  ExistingDir: String;
begin
#ifdef TestMode
  Result := RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{69C23A51-2744-48E0-9966-02F3CE16E601}_is1', 'InstallLocation', ExistingDir);
#else
  Result := RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9E81C3D8-0F3D-4D2E-A612-60AEB63C8C0C}_is1', 'InstallLocation', ExistingDir);
  if not Result then
  begin
    ExistingDir := ExpandConstant('{localappdata}\Programs\Smart PDF');
    Result := FileExists(AddBackslash(ExistingDir) + 'unins000.dat') and
      FileExists(AddBackslash(ExistingDir) + '_internal\python314.dll');
  end;
#endif
  Result := Result and FileExists(AddBackslash(ExistingDir) + 'SmartPDF.exe');
  if not Result then
    MsgBox('Nie znaleziono zainstalowanego Smart PDF. Pobierz pełny instalator z GitHub.', mbInformation, MB_OK);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpSelectTasks);
end;
#endif
