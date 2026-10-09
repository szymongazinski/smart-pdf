#define AppVersion "0.3.0"

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
Name: "pdfocr"; Description: "Dodaj Wykonaj OCR do menu prawego przycisku plików PDF"; GroupDescription: "Integracja z systemem Windows:"; Flags: checkedonce

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
#ifdef TestMode
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SmartPDFTest.OCR"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Smart PDF Test — wykonaj OCR"; Flags: uninsdeletekey; Tasks: pdfocr
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SmartPDFTest.OCR\command"; ValueType: string; ValueData: """{app}\SmartPDF.exe"" --ocr-in-place ""%1"""; Tasks: pdfocr
#else
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SmartPDF.OCR"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Smart PDF — wykonaj OCR"; Flags: uninsdeletekey; Tasks: pdfocr
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SmartPDF.OCR"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\SmartPDF.exe,0"; Tasks: pdfocr
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SmartPDF.OCR"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Single"; Tasks: pdfocr
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SmartPDF.OCR\command"; ValueType: string; ValueData: """{app}\SmartPDF.exe"" --ocr-in-place ""%1"""; Tasks: pdfocr
#endif
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
#ifdef UpdateOnly
Filename: "{app}\SmartPDF.exe"; Flags: nowait; Check: LaunchUpdatedProgram
#else
Filename: "{app}\SmartPDF.exe"; Description: "Uruchom Smart PDF"; Flags: nowait postinstall skipifsilent
#endif

[Code]
#ifdef TestMode
const SettingsKey = 'Software\SmartPDFInstallerTest\Smart PDF';
#else
const SettingsKey = 'Software\SmartPDF\Smart PDF';
#endif
var
  OCRPage: TWizardPage;
  OCREngine, OCRQuality, OCRLanguage: TNewComboBox;

procedure AddLabel(Text: String; Top: Integer);
var LabelControl: TNewStaticText;
begin
  LabelControl := TNewStaticText.Create(OCRPage);
  LabelControl.Parent := OCRPage.Surface;
  LabelControl.Caption := Text;
  LabelControl.Top := ScaleY(Top);
end;

function AddCombo(Top: Integer): TNewComboBox;
begin
  Result := TNewComboBox.Create(OCRPage);
  Result.Parent := OCRPage.Surface;
  Result.Top := ScaleY(Top);
  Result.Width := OCRPage.SurfaceWidth;
  Result.Style := csDropDownList;
end;

procedure InitializeWizard();
var CurrentEngine, CurrentLanguage: String; CurrentDPI: Cardinal;
begin
  OCRPage := CreateCustomPage(wpSelectTasks, 'Konfiguracja lokalnego OCR', 'Tekst rozpoznawany jest na tym komputerze. Ustawienia można zmienić w programie.');
  AddLabel('Obliczenia', 4);
  OCREngine := AddCombo(23);
  OCREngine.Items.Add('GPU, jeśli dostępne (zalecane) — DirectML, z przejściem na CPU');
  OCREngine.Items.Add('Tylko procesor (CPU) — dokładny model PP-OCRv5');
  OCREngine.Items.Add('GPU — DirectML (wymaga zgodnej karty i sterownika)');
  OCREngine.Items.Add('Tylko procesor (CPU) — Tesseract LSTM');
  OCREngine.ItemIndex := 0;
  RegQueryStringValue(HKCU, SettingsKey, 'ocr_engine', CurrentEngine);
  CurrentEngine := ExpandConstant('{param:OCRENGINE|' + CurrentEngine + '}');
  if CurrentEngine = 'cpu' then OCREngine.ItemIndex := 1;
  if CurrentEngine = 'gpu' then OCREngine.ItemIndex := 2;
  if CurrentEngine = 'tesseract' then OCREngine.ItemIndex := 3;
  AddLabel('Języki', 65);
  OCRLanguage := AddCombo(84);
  OCRLanguage.Items.Add('Polski i angielski');
  OCRLanguage.Items.Add('Polski');
  OCRLanguage.Items.Add('Angielski');
  OCRLanguage.ItemIndex := 0;
  RegQueryStringValue(HKCU, SettingsKey, 'ocr_languages', CurrentLanguage);
  CurrentLanguage := ExpandConstant('{param:OCRLANG|' + CurrentLanguage + '}');
  if CurrentLanguage = 'pol' then OCRLanguage.ItemIndex := 1;
  if CurrentLanguage = 'eng' then OCRLanguage.ItemIndex := 2;
  AddLabel('Jakość rozpoznawania', 126);
  OCRQuality := AddCombo(145);
  OCRQuality.Items.Add('300 DPI — dokładna (zalecana)');
  OCRQuality.Items.Add('400 DPI — bardzo drobny tekst');
  OCRQuality.Items.Add('200 DPI — szybsza');
  OCRQuality.ItemIndex := 0;
  CurrentDPI := 300;
  RegQueryDWordValue(HKCU, SettingsKey, 'ocr_dpi', CurrentDPI);
  CurrentDPI := StrToIntDef(ExpandConstant('{param:OCRDPI|' + IntToStr(CurrentDPI) + '}'), 300);
  if CurrentDPI = 400 then OCRQuality.ItemIndex := 1;
  if CurrentDPI = 200 then OCRQuality.ItemIndex := 2;
  AddLabel('Modele są dołączone. OCR działa bez internetu i nie wysyła PDF-ów.', 194);
  AddLabel('Przy podmianie pliku zachowujemy lokalną kopię oryginału.', 216);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Engine, Languages: String; DPI: Cardinal;
begin
  if CurStep = ssPostInstall then
  begin
    Engine := 'auto';
    if OCREngine.ItemIndex = 1 then Engine := 'cpu';
    if OCREngine.ItemIndex = 2 then Engine := 'gpu';
    if OCREngine.ItemIndex = 3 then Engine := 'tesseract';
    Languages := 'pol+eng';
    if OCRLanguage.ItemIndex = 1 then Languages := 'pol';
    if OCRLanguage.ItemIndex = 2 then Languages := 'eng';
    DPI := 300;
    if OCRQuality.ItemIndex = 1 then DPI := 400;
    if OCRQuality.ItemIndex = 2 then DPI := 200;
    RegWriteStringValue(HKCU, SettingsKey, 'ocr_engine', Engine);
    RegWriteStringValue(HKCU, SettingsKey, 'ocr_languages', Languages);
    RegWriteDWordValue(HKCU, SettingsKey, 'ocr_dpi', DPI);
  end;
end;

#ifdef UpdateOnly
function LaunchUpdatedProgram(): Boolean;
begin
  Result := ExpandConstant('{param:NOOPEN|0}') <> '1';
end;

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
  if PageID = OCRPage.ID then
    Result := RegValueExists(HKCU, SettingsKey, 'ocr_engine');
end;
#endif
