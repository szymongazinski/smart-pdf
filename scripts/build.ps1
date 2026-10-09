param([switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
python scripts/fetch_ocr.py
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się pobrać modeli OCR.' }
python -m PyInstaller --noconfirm SmartPDF.spec
if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zbudować programu.' }
if (-not $SkipInstaller) {
    $compilerPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $compiler = $compilerPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $compiler) { throw 'Zainstaluj Inno Setup 6: winget install JRSoftware.InnoSetup' }
    & $compiler 'installer/SmartPDF.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zbudować instalatora.' }
}
