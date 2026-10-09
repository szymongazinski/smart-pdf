# Third-party software

Smart PDF is distributed under AGPL-3.0-or-later. Complete corresponding application
source, build scripts and release tags are at https://github.com/szymongazinski/smart-pdf.

* **PyMuPDF / MuPDF** (Artifex): AGPL-3.0-or-later, https://pymupdf.readthedocs.io/
  and https://github.com/pymupdf/PyMuPDF. PyMuPDF includes MuPDF and its OCR integration.
* **PySide6 / Shiboken6 / Qt** (The Qt Company): LGPL-3.0 / GPL-3.0 / commercial
  options. This distribution uses the LGPL option and replaceable shared Qt DLLs.
  Sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ and
  https://code.qt.io/cgit/qt/qtbase.git/. See bundled wheel notices for individual
  components and https://www.qt.io/licensing/open-source-lgpl-obligations.
  Modifying/replacing these libraries and reverse engineering for debugging such
  modifications are permitted. Run from source or replace compatible libraries
  in `_internal/PySide6`; the installer does not impose signature checks.
* **Tesseract** and **tessdata_best** (Tesseract contributors): Apache-2.0,
  https://github.com/tesseract-ocr/tesseract and
  https://github.com/tesseract-ocr/tessdata_best. Model revision and SHA256 digests
  are in `assets/ocr-models.json`.
* **Python** (Python Software Foundation): PSF License,
  https://docs.python.org/3/license.html. Runtime license is included by PyInstaller.
* **PyInstaller**: GPL-2.0-or-later with a distribution exception,
  https://pyinstaller.org/en/stable/license.html. Applications bundled by
  PyInstaller retain their own license.

Full AGPL, GPL-3.0, LGPL-3.0 and Apache-2.0 texts accompany the application.
Additional upstream notices from the wheels are retained in the application bundle.
System fonts are used from Windows; no proprietary font files are distributed.
