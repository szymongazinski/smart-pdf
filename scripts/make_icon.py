"""Convert the repository's vector icon to Windows ICO for the installer."""
from pathlib import Path
from PySide6.QtCore import QRectF
from PySide6.QtGui import QGuiApplication,QImage,QPainter
from PySide6.QtSvg import QSvgRenderer

root = Path(__file__).resolve().parents[1]
app = QGuiApplication([])
image = QImage(256,256,QImage.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
QSvgRenderer(str(root/"assets/smart-pdf.svg")).render(painter,QRectF(0,0,256,256))
painter.end()
if not image.save(str(root/"assets/smart-pdf.ico"),"ICO"):
    raise RuntimeError("Nie można zapisać ikony ICO")
