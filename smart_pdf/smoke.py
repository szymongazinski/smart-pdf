"""Packaged-application integration check, isolated from the user's settings."""
import json
from pathlib import Path

import pymupdf
from PySide6.QtCore import QTimer,QPointF
from PySide6.QtTest import QTest

from smart_pdf.export import export_pdf
from smart_pdf.model import Project,make_object,text_html


def run_smoke(app,window,directory,preview_path=None):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    def check():
        try:
            project = Project.blank()
            project.title = "Smart PDF smoke test"
            obj = make_object("text",40,70,440,130,html=text_html("Smart PDF — działa\nZażółć gęślą jaźń",20,"#2864ed",True,True))
            project.pages[0].objects.append(obj)
            project.add_margin([0],"right",90)
            window.attach_project(project)
            window.ocr_action.setChecked(False)
            window.canvas.select_ids([obj["id"]])
            window.mutate("Rotate",lambda:setattr(project.pages[0],"rotation",90))
            window.undo.undo()
            assert project.pages[0].rotation==0
            window.undo.redo()
            assert project.pages[0].rotation==90
            project.save(directory/"smoke.smartpdf")
            restored = Project.load(directory/"smoke.smartpdf")
            assert restored.pages==project.pages
            export_pdf(restored,directory/"smoke.pdf")
            with pymupdf.open(directory/"smoke.pdf") as result:
                assert "Zażółć gęślą jaźń" in result[0].get_text()
                assert result[0].rotation==90
                result[0].get_pixmap().save(directory/"smoke-export.png")
            window.canvas.fit_page()
            QTest.qWait(250)
            window.grab().save(str(directory/"smoke-window.png"))
            if preview_path:
                # Optional local rendering check; documents never leave this machine.
                preview = Project.from_pdf(preview_path)
                window.attach_project(preview)
                index = min(1,len(preview.pages)-1)
                for zoom in (125,175,210,300):
                    window.canvas.set_zoom(zoom)
                    window.canvas.centerOn(window.canvas.roots[index].mapToScene(QPointF(301,240)))
                    QTest.qWait(150)
                    window.canvas.update_visible_pages()
                    while window.canvas.render_queue:
                        window.canvas.render_next_tile()
                    window.canvas.remove_old_tiles()
                    window.grab().save(str(directory/f"preview-window-{zoom}.png"))
                    window.canvas.viewport().grab().save(str(directory/f"preview-page-{zoom}.png"))
            (directory/"result.json").write_text(json.dumps({"ok":True,"pages":len(project.pages),"fonts":"Polish Unicode verified","rotation":90}),encoding="utf-8")
            window.undo.setClean()
            window.recovered = False
            project.dirty = False
            window.close()
            app.exit(0)
        except Exception as error:
            (directory/"result.json").write_text(json.dumps({"ok":False,"error":str(error)}),encoding="utf-8")
            app.exit(1)
    QTimer.singleShot(300,check)
