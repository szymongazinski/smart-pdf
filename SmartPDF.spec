# PyInstaller one-directory build supports Qt LGPL library replacement.
from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata,collect_data_files,collect_dynamic_libs

root = Path(SPECPATH)
data = [(str(root / 'assets'), 'assets'), (str(root / 'LICENSE'), '.'),
        (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
        (str(root / 'licenses'), 'licenses')]
for distribution in ('PyMuPDF','PySide6-Essentials','shiboken6','rapidocr','onnxruntime-directml',
                     'numpy','opencv-python-headless','Pillow','pyclipper','Shapely','omegaconf',
                     'PyYAML','six','tqdm','requests','colorlog','flatbuffers','protobuf',
                     'packaging','certifi','charset-normalizer','idna','urllib3'):
    data += copy_metadata(distribution)
data += collect_data_files('rapidocr',includes=['*.yaml'])
data += collect_data_files('onnxruntime',includes=['LICENSE','Privacy.md','ThirdPartyNotices.txt'])
a = Analysis(['run.py'], pathex=[str(root)], binaries=collect_dynamic_libs('onnxruntime'), datas=data,
             hiddenimports=['pymupdf','rapidocr.inference_engine.onnxruntime.main'], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtPdf',
                       'PySide6.QtQuick','PySide6.QtQml','PySide6.QtNetwork','pytest',
                       'torch','paddle','tensorflow','sympy','onnxruntime.tools','onnxruntime.quantization'], noarchive=False)
# Qt on Windows uses the operating system's unversioned ICU API. An unrelated
# Poppler/Conda ICU on PATH may otherwise be collected with incompatible exports.
# MuPDF statically links its text libraries and does not need these foreign DLLs.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() != 'icuuc.dll'
              and not Path(entry[0]).name.lower().startswith('icudt')]
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='SmartPDF',debug=False,
          bootloader_ignore_signals=False,strip=False,upx=False,console=False,
          icon=str(root / 'assets' / 'smart-pdf.ico'))
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SmartPDF')
