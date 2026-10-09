"""Make a public, synthetic demo and screenshots; never uses personal documents."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication,QEvent,QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import pymupdf
from smart_pdf.export import export_pdf,overlay_pdf
from smart_pdf.model import Project,make_object,text_html
from smart_pdf.window import MainWindow

root = Path(__file__).resolve().parents[1]
output = root/"output"
output.mkdir(exist_ok=True)
app = QApplication([])
app.setStyle("Fusion")
app.setOrganizationName("SmartPDF-QA")
app.setApplicationName("SmartPDF-QA")
if os.name=="nt":
    for name in ("arial.ttf","arialbd.ttf","ariali.ttf","arialbi.ttf","segoeui.ttf","segoeuib.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"])/"Fonts"/name))
base = Project.blank()
page = base.pages[0]
page.objects.append(make_object("text",42,42,505,58,html=text_html("Miejsce na dobre pomysły",27,"#20385f",True)))
page.objects.append(make_object("text",42,111,500,65,html=text_html("Smart PDF  /  Przykładowy dokument\nTen plik zawiera wyłącznie fikcyjne dane.",12,"#72829c")))
page.objects.append(make_object("line",48,200,490,1,color="#d7dfeb",width=1))
page.objects.append(make_object("text",42,230,495,190,html=text_html("Zaznacz tekst i dodaj kolor.\n\nRozwijaj notatki na marginesie, rysuj i przesuwaj pola tekstowe. Dokument pozostaje czytelny, a projekt zachowuje wszystkie obiekty.\n\nPolskie znaki: zażółć gęślą jaźń.",16,"#25324a")))
base_pdf = overlay_pdf(page)
(output/"SmartPDF-demo-source.pdf").write_bytes(base_pdf)
project = Project.from_pdf(output/"SmartPDF-demo-source.pdf")
with pymupdf.open(stream=project.source_pdf,filetype="pdf") as doc:
    original = doc.tobytes()
    for i in range(2):
        with pymupdf.open(stream=original,filetype="pdf") as one:
            doc.insert_pdf(one)
    from smart_pdf.model import PageState
    project = Project(doc.tobytes(),[PageState(i,p.rect.width,p.rect.height) for i,p in enumerate(doc)])
project.title = "Smart PDF — przykład"
project.add_margin([0],"right",150)
notes = project.pages[0].objects[0]
notes["html"] = text_html("Moje notatki\n\n• nowy pomysł\n• pytanie do tekstu\n• ważny fragment",13,"#285ade",True)
notes["h"] = 320
rect = project.doc[0].search_for("Zaznacz tekst i dodaj kolor.")[0]
project.pages[0].objects.append(make_object("highlight",rect.x0,rect.y0,rect.width,rect.height,color="#ffcf40",opacity=.36,rects=[[0,0,1,1]]))
project.pages[0].objects.append(make_object("pen",60,478,270,70,color="#ef4d64",width=3,points=[[0,.8],[.15,.3],[.3,.75],[.48,.1],[.65,.7],[.82,.35],[1,.6]]))
project.pages[0].objects.append(make_object("ellipse",65,590,90,90,color="#43ad87",width=3))
project.pages[0].objects.append(make_object("triangle",205,590,95,90,color="#8b66dc",fill="#eee8ff",width=3))
project.pages[0].objects.append(make_object("text",352,575,180,90,rotation=-12,html=text_html("Możesz mnie\nprzesunąć i obrócić",15,"#285ade",True,True)))
project.save(output/"SmartPDF-demo.smartpdf")
export_pdf(project,output/"SmartPDF-demo.pdf")
with pymupdf.open(output/"SmartPDF-demo.pdf") as doc:
    doc[0].get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(output/"SmartPDF-export-preview.png")
window = MainWindow()
window.resize(1500,980)
window.show()
window.ocr_action.setChecked(False)
window.attach_project(project)
QTest.qWait(450)
window.canvas.select_ids([project.pages[0].objects[-1]["id"]])
window.grab().save(str(output/"SmartPDF-editor.png"))
window.canvas.start_text_edit(notes["id"])
QTest.qWait(150)
window.grab().save(str(output/"SmartPDF-inline.png"))
window.canvas.finish_text_edit()
window.canvas.set_zoom(250)
window.canvas.centerOn(window.canvas.root.mapToScene(260,275))
QTest.qWait(400)
window.grab().save(str(output/"SmartPDF-zoom.png"))
window.read_action.setChecked(True)
window.toggle_reading(True)
app.processEvents()
window.canvas.fit_page()
QTest.qWait(300)
window.grab().save(str(output/"SmartPDF-reading.png"))
window.undo.clear()
window.close()
app.clipboard().clear()
print(output)
