import copy

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from smart_pdf.model import Project,make_object,text_html
from smart_pdf.window import MainWindow


def create_window(app):
    window = MainWindow()
    window.ocr_action.setChecked(False)
    window.resize(1280,850)
    window.show()
    window.attach_project(Project.blank())
    app.processEvents()
    return window


def finish(window,app):
    window.undo.clear()
    window.project.dirty = False
    window.recovered = False
    window.close()
    window.deleteLater()
    app.processEvents()


def view_point(canvas,x,y):
    return canvas.mapFromScene(canvas.root.mapToScene(QPointF(x,y)))


def test_draw_undo_redo_and_dirty_state(app):
    window = create_window(app)
    canvas = window.canvas
    canvas.set_tool("pen")
    QTest.mousePress(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,60,100))
    QTest.mouseMove(canvas.viewport(),view_point(canvas,80,115),20)
    QTest.mouseMove(canvas.viewport(),view_point(canvas,130,145),20)
    QTest.mouseRelease(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,130,145))
    app.processEvents()
    assert len(window.project.pages[0].objects)==1
    assert window.project.pages[0].objects[0]["kind"]=="pen"
    assert window.project.dirty
    canvas.setFocus()
    QTest.keyClick(canvas,Qt.Key_Z,Qt.ControlModifier)
    app.processEvents()
    assert not window.project.pages[0].objects
    assert window.undo.isClean()
    assert not window.project.dirty
    QTest.keyClick(canvas,Qt.Key_Y,Qt.ControlModifier)
    app.processEvents()
    assert len(window.project.pages[0].objects)==1
    finish(window,app)


def test_object_clipboard_cut_paste_and_undo(app):
    window = create_window(app)
    obj = make_object("ellipse",40,50,100,70)
    window.mutate("Add",lambda:window.project.pages[0].objects.append(obj))
    canvas = window.canvas
    canvas.select_ids([obj["id"]])
    canvas.setFocus()
    QTest.keyClick(canvas,Qt.Key_C,Qt.ControlModifier)
    QTest.keyClick(canvas,Qt.Key_V,Qt.ControlModifier)
    app.processEvents()
    assert len(window.project.pages[0].objects)==2
    assert len({o["id"] for o in window.project.pages[0].objects})==2
    assert canvas.selected_objects()[0]["x"]==56
    QTest.keyClick(canvas,Qt.Key_X,Qt.ControlModifier)
    app.processEvents()
    assert len(window.project.pages[0].objects)==1
    window.undo.undo()
    assert len(window.project.pages[0].objects)==2
    finish(window,app)


def test_direct_move_resize_rotate_and_properties(app):
    window = create_window(app)
    obj = make_object("text",80,120,180,80,html=text_html("Editable",16))
    window.mutate("Add",lambda:window.project.pages[0].objects.append(obj))
    canvas = window.canvas
    canvas.select_ids([obj["id"]])
    QTest.mousePress(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,130,150))
    QTest.mouseMove(canvas.viewport(),view_point(canvas,160,180),25)
    QTest.mouseRelease(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,160,180))
    app.processEvents()
    moved = window.project.pages[0].objects[0]
    assert moved["x"]>100 and moved["y"]>140
    canvas.select_ids([obj["id"]])
    window.set_property("rotation",45)
    assert window.project.pages[0].objects[0]["rotation"]==45
    window.undo.undo()
    assert window.project.pages[0].objects[0]["rotation"]==0
    canvas.select_ids([obj["id"]])
    current = window.project.pages[0].objects[0]
    x,y,w,h = current["x"],current["y"],current["w"],current["h"]
    QTest.mousePress(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,x+w,y+h))
    QTest.mouseMove(canvas.viewport(),view_point(canvas,x+w+40,y+h+30),25)
    QTest.mouseRelease(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,x+w+40,y+h+30))
    app.processEvents()
    assert window.project.pages[0].objects[0]["w"]>w+25
    assert window.project.pages[0].objects[0]["h"]>h+20
    finish(window,app)


def test_reading_hides_panels_and_blocks_editing(app):
    window = create_window(app)
    window.read_action.setChecked(True)
    window.toggle_reading(True)
    assert not window.tools.isVisible()
    assert not window.properties_dock.isVisible()
    assert not window.pages_dock.isVisible()
    window.mutate("Must not edit",lambda:window.project.pages[0].objects.append(make_object("rect")))
    assert not window.project.pages[0].objects
    window.toggle_reading(False)
    assert window.tools.isVisible()
    assert window.properties_dock.isVisible()
    finish(window,app)


def test_search_field_does_not_trigger_tool_shortcuts(app):
    window = create_window(app)
    window.search.setFocus()
    QTest.keyClicks(window.search,"plain text")
    assert window.search.text()=="plain text"
    assert window.canvas.tool=="select"
    finish(window,app)


def test_text_selection_highlight_uses_local_geometry_and_undo(app,tmp_path):
    import pymupdf
    with pymupdf.open() as doc:
        doc.new_page().insert_text((45,80),"One two three",fontsize=18)
        doc.save(tmp_path/"select.pdf")
    window = create_window(app)
    window.attach_project(Project.from_pdf(tmp_path/"select.pdf"))
    app.processEvents()
    canvas = window.canvas
    canvas.set_tool("highlight")
    first,last = canvas.words[0],canvas.words[-1]
    QTest.mousePress(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,(first[0]+first[2])/2,(first[1]+first[3])/2))
    QTest.mouseMove(canvas.viewport(),view_point(canvas,(last[0]+last[2])/2,(last[1]+last[3])/2),20)
    QTest.mouseRelease(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,(last[0]+last[2])/2,(last[1]+last[3])/2))
    app.processEvents()
    obj = window.project.pages[0].objects[0]
    assert obj["kind"]=="highlight"
    assert obj["rects"]==[[0,0,1,1]]
    window.undo.undo()
    assert not window.project.pages[0].objects
    finish(window,app)


def test_ocr_disabled_does_not_start_child_process(app):
    window = create_window(app)
    window.ocr_action.setChecked(False)
    window.start_ocr()
    from PySide6.QtCore import QProcess
    assert window.ocr_process.state()==QProcess.NotRunning
    finish(window,app)


def test_background_ocr_child_process_and_cancel(app,tmp_path):
    import time
    import pymupdf
    from smart_pdf.export import overlay_pdf
    from smart_pdf.ocr import available_languages
    from PySide6.QtCore import QProcess
    if not {"pol","eng"}<=set(available_languages()):
        __import__("pytest").skip("OCR models missing")
    source = Project.blank()
    source.pages[0].objects.append(make_object("text",40,50,480,120,html=text_html("Local OCR child process\nPolski oraz English",24)))
    with pymupdf.open(stream=overlay_pdf(source.pages[0]),filetype="pdf") as doc:
        png = doc[0].get_pixmap(dpi=180).tobytes("png")
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_image(page.rect,stream=png)
        doc.save(tmp_path/"scan.pdf")
    window = create_window(app)
    window.settings.setValue("ocr_languages","pol+eng")
    window.attach_project(Project.from_pdf(tmp_path/"scan.pdf"))
    window.start_ocr(True)
    deadline = time.monotonic()+20
    while time.monotonic()<deadline and (window.ocr_process.state()!=QProcess.NotRunning or window.ocr_current):
        QTest.qWait(10)
    assert 0 in window.project.ocr, window.ocr_status.text()
    assert "Local OCR child process" in " ".join(w[4] for w in window.project.words(0))
    window.start_ocr(True,True)
    assert window.ocr_process.state()!=QProcess.NotRunning
    window.cancel_ocr()
    assert window.ocr_process.state()==QProcess.NotRunning
    assert not window.ocr_queue
    finish(window,app)
