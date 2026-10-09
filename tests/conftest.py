import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from pathlib import Path
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("SmartPDFTests")
    app.setOrganizationName("SmartPDFTests")
    # Windows' headless Qt plugin cannot discover system fonts automatically.
    if os.name == "nt":
        for name in ("arial.ttf","arialbd.ttf","ariali.ttf","arialbi.ttf","segoeui.ttf","segoeuib.ttf"):
            path = Path(os.environ["WINDIR"])/"Fonts"/name
            if path.exists():
                QFontDatabase.addApplicationFont(str(path))
    yield app
    # The Windows offscreen clipboard retains QMimeData until Qt teardown.
    # Release test-owned content before the QApplication is destroyed.
    app.clipboard().clear()
    app.processEvents()
