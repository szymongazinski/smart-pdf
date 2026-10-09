import io
import hashlib

import pymupdf
import pytest
from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtTest import QTest

from smart_pdf.model import Project, make_object, text_html
from smart_pdf.updates import DOWNLOAD_PREFIX, choose_update, download_verified
from smart_pdf.window import MainWindow
from test_ui import create_window, finish, view_point


@pytest.mark.parametrize("tool",["select","select_text"])
def test_single_click_inline_text_and_local_undo(app,tool):
    window = create_window(app)
    obj = make_object("text",60,80,260,90,html=text_html("",18))
    window.mutate("Add",lambda:window.project.pages[0].objects.append(obj))
    canvas = window.canvas
    canvas.set_tool(tool)
    QTest.mouseClick(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,78,98))
    assert canvas.editing is not None
    QTest.keyClicks(canvas,"Hello")
    assert canvas.editing.editor.toPlainText()=="Hello"
    QTest.keyClick(canvas,Qt.Key_B,Qt.ControlModifier)
    QTest.keyClicks(canvas," bold")
    assert canvas.editing.editor.textCursor().charFormat().fontWeight()>=QFont.Bold
    QTest.keyClick(canvas,Qt.Key_Z,Qt.ControlModifier)
    assert canvas.editing is not None
    assert window.project.pages[0].objects  # Ctrl+Z must not delete the whole object.
    QTest.keyClick(canvas,Qt.Key_Y,Qt.ControlModifier)
    assert "Hello bold"==canvas.editing.editor.toPlainText()
    QTest.keyClick(canvas,Qt.Key_Escape)
    assert canvas.editing is None
    assert "Hello" in window.project.pages[0].objects[0]["html"]
    window.undo.undo()
    assert "Hello" not in window.project.pages[0].objects[0]["html"]
    finish(window,app)


def test_text_tool_creates_live_editor_and_native_clipboard(app):
    window = create_window(app)
    canvas = window.canvas
    canvas.set_tool("text")
    QTest.mouseClick(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,50,70))
    assert canvas.editing is not None
    app.clipboard().setText("Polski tekst")
    QTest.keyClick(canvas,Qt.Key_V,Qt.ControlModifier)
    assert canvas.editing.editor.toPlainText()=="Polski tekst"
    QTest.keyClick(canvas,Qt.Key_A,Qt.ControlModifier)
    QTest.keyClick(canvas,Qt.Key_C,Qt.ControlModifier)
    assert app.clipboard().text()=="Polski tekst"
    canvas.finish_text_edit()
    assert len(window.project.pages[0].objects)==1
    finish(window,app)


def test_typing_then_dragging_border_preserves_text_and_separate_undo(app):
    window = create_window(app)
    obj = make_object("text",70,100,220,70,html=text_html("",14))
    window.mutate("Add",lambda:window.project.pages[0].objects.append(obj))
    canvas = window.canvas
    canvas.start_text_edit(obj["id"])
    QTest.keyClicks(canvas,"Saved text")
    QTest.mousePress(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,120,100))
    QTest.mouseMove(canvas.viewport(),view_point(canvas,160,135),25)
    QTest.mouseRelease(canvas.viewport(),Qt.LeftButton,Qt.NoModifier,view_point(canvas,160,135))
    assert canvas.editing is None
    assert "Saved text" in window.project.pages[0].objects[0]["html"]
    assert window.project.pages[0].objects[0]["x"]>100
    window.undo.undo()
    assert window.project.pages[0].objects[0]["x"]==70
    assert "Saved text" in window.project.pages[0].objects[0]["html"]
    window.undo.undo()
    assert "Saved text" not in window.project.pages[0].objects[0]["html"]
    finish(window,app)


def test_cut_objects_on_multiple_visible_pages_is_undoable(app):
    from smart_pdf.model import PageState
    window = create_window(app)
    project = Project.blank()
    project.pages.append(PageState(0,project.pages[0].width,project.pages[0].height))
    objects = [make_object("ellipse",40,50,100,80),make_object("line",30,90,120,1)]
    for page,obj in zip(project.pages,objects):
        page.objects.append(obj)
    window.attach_project(project)
    window.canvas.set_tool("select")
    window.canvas.select_ids([o["id"] for o in objects])
    window.canvas.copy(cut=True)
    assert not any(p.objects for p in project.pages)
    window.undo.undo()
    assert all(len(p.objects)==1 for p in project.pages)
    finish(window,app)


def test_margin_is_immediate_unique_editable_and_live_resizable(app):
    window = create_window(app)
    window.add_margin()
    assert window.project.pages[0].margins["right"]>0
    assert window.canvas.editing is not None
    QTest.keyClicks(window.canvas,"My notes")
    window.canvas.finish_text_edit()
    window.add_margin()
    assert len(window.project.pages[0].objects)==1
    assert window.canvas.editing.editor.toPlainText()=="My notes"
    window.add_margin("left")
    assert len(window.project.pages[0].objects)==2
    assert window.project.pages[0].margins["left"]>0
    window.canvas.finish_text_edit()
    before = window.undo.count()
    window.begin_live_change()
    window.margin_width_changed(70)
    assert abs(window.project.pages[0].margins["left"]-70*72/25.4)<.01
    window.margin_width_changed(85)
    assert window.undo.count()==before
    notes = next(o for o in window.project.pages[0].objects if o["margin_side"]=="left")
    assert abs(notes["w"]-(85*72/25.4-16))<.01
    window.end_live_change()
    assert window.undo.count()==before+1
    window.undo.undo()
    assert abs(window.project.pages[0].margins["left"]-55*72/25.4)<.01
    assert "My notes" in next(o for o in window.project.pages[0].objects if o["margin_side"]=="right")["html"]
    right = next(o for o in window.project.pages[0].objects if o["margin_side"]=="right")
    window.canvas.start_text_edit(right["id"])
    assert window.margin_side=="right"
    window.canvas.finish_text_edit()
    finish(window,app)


def test_stroke_changes_during_slider_drag_and_undoes_once(app):
    window = create_window(app)
    obj = make_object("line",40,70,180,2)
    window.mutate("Add",lambda:window.project.pages[0].objects.append(obj))
    window.canvas.set_tool("select")
    window.canvas.select_ids([obj["id"]])
    before = window.undo.count()
    window.begin_live_change()
    window.stroke_changed(5)
    window.stroke_changed(9)
    assert window.canvas.items_by_id[obj["id"]].obj["width"]==9
    assert window.undo.count()==before
    window.end_live_change()
    window.undo.undo()
    assert window.project.pages[0].objects[0]["width"]==2
    finish(window,app)


@pytest.mark.parametrize("rotation",[90,180,270])
def test_new_margin_notes_are_upright_on_rotated_pages(app,rotation):
    window = create_window(app)
    window.mutate("Rotate",lambda:setattr(window.project.pages[0],"rotation",rotation))
    window.add_margin("right")
    item = window.canvas.editing
    start,end = item.mapToScene(QPointF(0,0)),item.mapToScene(QPointF(10,0))
    assert end.x()-start.x()>9.9
    assert abs(end.y()-start.y())<.01
    QTest.keyClicks(window.canvas,"Upright notes")
    window.canvas.finish_text_edit()
    assert len(window.project.pages[0].objects)==1
    finish(window,app)


def test_controls_keep_readable_numbers_and_thumbnail_hover(app):
    window = create_window(app)
    QTest.qWait(50)
    for spin in [window.page_number,window.font_size,window.margin_control.spin]:
        assert spin.lineEdit().width()>30
    assert window.page_list.hasMouseTracking()
    finish(window,app)


def test_continuous_scroll_and_zoom_uses_sharp_bounded_tiles(app,tmp_path):
    with pymupdf.open() as doc:
        for i in range(8):
            doc.new_page().insert_text((50,80),f"Page {i+1} sharp vector text",fontsize=18)
        doc.save(tmp_path/"pages.pdf")
    window = create_window(app)
    window.attach_project(Project.from_pdf(tmp_path/"pages.pdf"))
    canvas = window.canvas
    assert len(canvas.roots)==8
    canvas.scroll_to_page(5)
    QTest.qWait(100)
    assert window.index==5
    assert window.page_number.value()==6
    assert canvas.sceneRect().height()>6000
    canvas.set_zoom(400)
    canvas.update_visible_pages()
    while canvas.render_queue:
        canvas.render_next_tile()
    assert canvas.render_scale>=4*canvas.viewport().devicePixelRatioF()
    assert canvas.backgrounds
    assert all(item.pixmap().width()<=513 for item in canvas.backgrounds.values())
    assert canvas.tile_bytes<=64*1024*1024
    assert len({key[0] for key in canvas.backgrounds})<=2
    finish(window,app)


def test_ocr_starts_off_even_when_old_setting_was_on(app):
    QSettings().setValue("auto_ocr",True)
    window = MainWindow()
    assert not window.ocr_action.isChecked()
    assert list(window.tool_actions)[:2]==["select_text","select"]
    window.close()
    window.deleteLater()
    app.processEvents()


def test_update_selection_and_download_hash(tmp_path,monkeypatch):
    payload = b"test update payload"
    sha = hashlib.sha256(payload).hexdigest()
    asset = {"name":"SmartPDF-Update-0.3.0-x64.exe","digest":"sha256:"+sha,"size":len(payload),"browser_download_url":DOWNLOAD_PREFIX+"v0.3.0/SmartPDF-Update-0.3.0-x64.exe"}
    info = choose_update([{"tag_name":"v0.3.0","assets":[asset]}],"0.2.0")
    assert info["version"]=="0.3.0"
    assert choose_update([{"tag_name":"v0.2.0","assets":[asset]}],"0.2.0") is None
    monkeypatch.setattr("urllib.request.urlopen",lambda *args,**kwargs:io.BytesIO(payload))
    target = download_verified(info,tmp_path)
    assert __import__("pathlib").Path(target).read_bytes()==payload
    with pytest.raises(ValueError,match="Suma kontrolna"):
        download_verified({**info,"sha256":"0"*64},tmp_path)
    assert not list(tmp_path.glob("*.part"))
