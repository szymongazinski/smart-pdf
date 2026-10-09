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
* **RapidOCR / RapidAI** and the converted **PaddleOCR PP-OCRv5** models:
  Apache-2.0, https://github.com/RapidAI/RapidOCR and
  https://github.com/PaddlePaddle/PaddleOCR. Pinned model URLs and SHA256 hashes
  are in `assets/ppocr-models.json`. These models are used offline.
* **ONNX Runtime / DirectML** (Microsoft): MIT, https://github.com/microsoft/onnxruntime
  and https://github.com/microsoft/DirectML. Upstream licenses and notices are
  retained in the bundled wheel metadata and ONNX Runtime package.
* **Noto Sans** (Google / Noto contributors): SIL Open Font License 1.1.
  https://github.com/notofonts/noto-fonts. License: `licenses/NotoSans-OFL.txt`;
  source revision and checksum: `assets/font-source.json`. Embedded only for
  the invisible Unicode OCR layer; original document fonts are preserved.
* Neural OCR support libraries: **NumPy** (BSD-3-Clause), **OpenCV** (Apache-2.0),
  **Pillow** (HPND), **Shapely** (BSD-3-Clause, GEOS LGPL-2.1), **pyclipper**
  (MIT / Boost Software License), **OmegaConf** (BSD-3-Clause), **PyYAML** (MIT),
  **requests** (Apache-2.0), **urllib3** (MIT), **certifi** (MPL-2.0),
  **idna** and **charset-normalizer** (BSD-3-Clause / MIT), **six** (MIT),
  **tqdm** (MPL-2.0 / MIT), **colorlog** (MIT), **flatbuffers** (Apache-2.0),
  **protobuf** (BSD-3-Clause), and **packaging** (Apache-2.0 / BSD-2-Clause).
  Respective upstream license files are retained in bundled package metadata.
* **Python** (Python Software Foundation): PSF License,
  https://docs.python.org/3/license.html. Runtime license is included by PyInstaller.
* **PyInstaller**: GPL-2.0-or-later with a distribution exception,
  https://pyinstaller.org/en/stable/license.html. Applications bundled by
  PyInstaller retain their own license.

Full AGPL, GPL-3.0, LGPL-3.0 and Apache-2.0 texts accompany the application.
Additional upstream notices from the wheels are retained in the application bundle.
System fonts are used from Windows; no proprietary font files are distributed.
