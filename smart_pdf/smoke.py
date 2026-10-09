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


def run_ocr_smoke(app,directory,engine="auto"):
    """Exercise the real context-menu dialog, subprocess and atomic replacement."""
    import hashlib,time
    from PySide6.QtCore import QSettings
    from smart_pdf.export import overlay_pdf
    from smart_pdf.ocr_dialog import OCRFileDialog
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    project = Project.blank()
    project.pages[0].objects.append(make_object("text",45,60,490,150,
        html=text_html("Dokument Smart PDF\nPolski tekst: Zażółć gęślą jaźń.\nEnglish text: The quick brown fox.",22,"#111111")))
    with pymupdf.open(stream=overlay_pdf(project.pages[0]),filetype="pdf") as vector:
        png = vector[0].get_pixmap(dpi=200).tobytes("png")
    source = directory/"OCR test — polski.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_image(page.rect,stream=png)
        page.set_rotation(270)
        doc.new_page().insert_text((40,80),"Native selectable text stays unchanged",fontsize=16)
        doc.save(source)
    original = source.read_bytes()
    (directory/"original.pdf").write_bytes(original)
    project.doc.close()
    QSettings().setValue("ocr_engine",engine)
    QSettings().setValue("ocr_languages","pol+eng")
    QSettings().setValue("ocr_dpi",300)
    dialog = OCRFileDialog(source)
    dialog.show()
    started = time.monotonic()
    timer = QTimer(dialog)
    timer.setInterval(150)
    def check():
        if not dialog.ocr_result and time.monotonic()-started<55 and not dialog.label.text().startswith("Nie udało"):
            return
        timer.stop()
        try:
            assert dialog.ocr_result,dialog.detail.text()
            report = dialog.ocr_result
            assert report["changed"] and report["pages_done"]==1 and report["pages_skipped"]==1
            assert Path(report["backup"]).read_bytes()==original
            with pymupdf.open(stream=original,filetype="pdf") as before,pymupdf.open(source) as after:
                assert "Zażółć" in after[0].get_text()
                assert "quick" in after[0].get_text()
                for a,b in zip(before,after):
                    assert a.get_pixmap().samples==b.get_pixmap().samples
                    assert a.rotation==b.rotation
            dialog.grab().save(str(directory/"ocr-dialog.png"))
            (directory/"result.json").write_text(json.dumps({"ok":True,"report":report}),encoding="utf-8")
            dialog.reject()
            app.exit(0)
        except Exception as error:
            dialog.grab().save(str(directory/"ocr-error.png"))
            (directory/"result.json").write_text(json.dumps({"ok":False,"error":str(error)}),encoding="utf-8")
            dialog.reject()
            app.exit(1)
    timer.timeout.connect(check)
    timer.start()
    return dialog
