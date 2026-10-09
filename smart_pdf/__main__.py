import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--ocr-worker":
        from smart_pdf.ocr import run_worker
        try:
            run_worker(*sys.argv[2:])
        except Exception as error:
            # Windowed builds have no stderr; an error sidecar remains observable.
            if len(sys.argv) > 3:
                Path(sys.argv[3] + ".error").write_text(str(error), encoding="utf-8")
            return 1
        return 0
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QColor,QIcon,QPalette
    from PySide6.QtWidgets import QApplication
    from smart_pdf.ocr import resources
    from smart_pdf.window import MainWindow
    smoke = len(sys.argv)>2 and sys.argv[1]=="--self-test"
    QCoreApplication.setOrganizationName("SmartPDFSmoke" if smoke else "SmartPDF")
    QCoreApplication.setApplicationName("SmartPDFSmoke" if smoke else "Smart PDF")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    for role,value in [(QPalette.Window,"#f6f8fc"),(QPalette.WindowText,"#25324a"),
                       (QPalette.Base,"#ffffff"),(QPalette.AlternateBase,"#f3f6fc"),
                       (QPalette.Text,"#25324a"),(QPalette.Button,"#ffffff"),
                       (QPalette.ButtonText,"#25324a"),(QPalette.Highlight,"#2864ed"),
                       (QPalette.HighlightedText,"#ffffff"),(QPalette.PlaceholderText,"#8290a5"),
                       (QPalette.ToolTipBase,"#ffffff"),(QPalette.ToolTipText,"#25324a")]:
        palette.setColor(role,QColor(value))
    app.setPalette(palette)
    app.setWindowIcon(QIcon(str(resources() / "smart-pdf.ico")))
    window = MainWindow()
    window.show()
    if smoke:
        from smart_pdf.smoke import run_smoke
        run_smoke(app,window,sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        window.open_path(sys.argv[1])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
