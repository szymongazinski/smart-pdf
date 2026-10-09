# PyInstaller one-directory build supports Qt LGPL library replacement.
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
data = [(str(root / 'assets'), 'assets'), (str(root / 'LICENSE'), '.'),
        (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
        (str(root / 'licenses'), 'licenses')]
for distribution in ('PyMuPDF','PySide6-Essentials','shiboken6'):
    data += copy_metadata(distribution)
a = Analysis(['run.py'], pathex=[str(root)], binaries=[], datas=data,
             hiddenimports=['pymupdf'], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtPdf',
                       'PySide6.QtQuick','PySide6.QtQml','PySide6.QtNetwork','pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='SmartPDF',debug=False,
          bootloader_ignore_signals=False,strip=False,upx=False,console=False,
          icon=str(root / 'assets' / 'smart-pdf.ico'))
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SmartPDF')
