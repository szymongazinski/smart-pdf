import hashlib
import json
import os
import time
from pathlib import Path

import pymupdf
import pytest
from PySide6.QtCore import QProcess,QSettings
from PySide6.QtTest import QTest

from smart_pdf.export import overlay_pdf
from smart_pdf.model import Project,make_object,text_html
from smart_pdf.ocr import page_layer,resources
from smart_pdf.ocr_file import commit_ocr,file_hash,prepare_ocr
from smart_pdf.ocr_dialog import OCRFileDialog


def create_scan(path,rotation=0,crop=False,encrypted=False):
    project = Project.blank()
    state = project.pages[0]
    state.objects.append(make_object("text",45,60,490,150,
                         html=text_html("Dokument Smart PDF\nPolski tekst: Zażółć gęślą jaźń.\nEnglish text: The quick brown fox.",22,"#111111")))
    with pymupdf.open(stream=overlay_pdf(state),filetype="pdf") as vector:
        pix = vector[0].get_pixmap(dpi=200)
    with pymupdf.open() as doc:
        page = doc.new_page(width=state.width,height=state.height)
        page.insert_image(page.rect,stream=pix.tobytes("png"))
        if crop:
            page.set_cropbox(pymupdf.Rect(20,30,570,800))
        page.set_rotation(rotation)
        page.add_text_annot((50,250),"Preserved annotation")
        page.insert_link({"kind":pymupdf.LINK_URI,"from":pymupdf.Rect(50,240,180,270),"uri":"https://example.com"})
        page = doc.new_page()
        page.insert_text((40,80),"Native vector text must stay unchanged",fontsize=16)
        page.draw_rect(pymupdf.Rect(40,100,180,150),color=(1,0,0))
        doc.set_metadata({"title":"OCR preservation test","author":"Fixture"})
        doc.set_toc([[1,"Scan",1],[1,"Native page",2]])
        doc.embfile_add("fixture.txt",b"Keep this attachment")
        options = {"encryption":pymupdf.PDF_ENCRYPT_AES_256,"owner_pw":"owner","user_pw":"secret"} if encrypted else {}
        doc.save(path,**options)
    project.doc.close()


@pytest.mark.parametrize("rotation,crop",[(0,False),(90,False),(180,True),(270,True)])
def test_ocr_preserves_original_pixels_pages_metadata_and_links(app,tmp_path,rotation,crop):
    source,output = tmp_path/"oryginał ze spacją.pdf",tmp_path/"result.pdf"
    create_scan(source,rotation,crop)
    original = source.read_bytes()
    report = prepare_ocr(source,output,engine="auto")
    assert source.read_bytes()==original
    assert report["pages_done"]==1 and report["pages_skipped"]==1
    with pymupdf.open(source) as before,pymupdf.open(output) as after:
        assert len(after)==len(before)
        assert before.metadata==after.metadata
        assert before.get_toc()==after.get_toc()
        assert before.embfile_get("fixture.txt")==after.embfile_get("fixture.txt")
        for a,b in zip(before,after):
            assert a.rotation==b.rotation and a.cropbox==b.cropbox
            assert a.get_pixmap(dpi=100,annots=True).samples==b.get_pixmap(dpi=100,annots=True).samples
            assert len(list(a.annots() or []))==len(list(b.annots() or []))
            assert [v["uri"] for v in a.get_links()]==[v["uri"] for v in b.get_links()]
        assert "Smart" in after[0].get_text()
        assert "Zażółć" in after[0].get_text()
        first = next(w for w in after[0].get_text("words") if w[4]=="Dokument")
        assert 45<first[0]+after[0].cropbox.x0<70
        assert 60<first[1]+after[0].cropbox.y0<95
        assert after[1].get_text()==before[1].get_text()
        image_before = before.extract_image(before[0].get_images()[0][0])["image"]
        image_after = after.extract_image(after[0].get_images()[0][0])["image"]
        assert image_before==image_after
    done = commit_ocr(source,output,report,tmp_path/"backups")
    assert Path(done["backup"]).read_bytes()==original
    assert file_hash(source)!=hashlib.sha256(original).hexdigest()
    assert not output.exists()


def test_encrypted_ocr_retains_encryption_and_password(app,tmp_path):
    source,output = tmp_path/"protected.pdf",tmp_path/"result.pdf"
    create_scan(source,encrypted=True)
    original = source.read_bytes()
    with pytest.raises(PermissionError):
        prepare_ocr(source,output,engine="tesseract",password="wrong")
    assert source.read_bytes()==original
    report = prepare_ocr(source,output,engine="tesseract",password="secret")
    commit_ocr(source,output,report,tmp_path/"backups")
    with pymupdf.open(source) as result:
        assert result.needs_pass
        assert result.authenticate("secret")
        assert "Dokument Smart PDF" in result[0].get_text()


def test_ocr_preserves_interactive_form_values(app,tmp_path):
    source,output = tmp_path/"form.pdf",tmp_path/"result.pdf"
    create_scan(source)
    with pymupdf.open(source) as doc:
        widget = pymupdf.Widget()
        widget.field_name = "retained-field"
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_value = "Editable value"
        widget.rect = pymupdf.Rect(45,250,200,280)
        doc[0].add_widget(widget)
        doc.saveIncr()
    prepare_ocr(source,output,engine="tesseract")
    with pymupdf.open(output) as result:
        page = result[0]
        widgets = list(page.widgets())
        assert len(widgets)==1
        assert widgets[0].field_name=="retained-field"
        assert widgets[0].field_value=="Editable value"
        widgets[0].field_value = "Still editable"
        widgets[0].update()
        assert list(page.widgets())[0].field_value=="Still editable"


def test_native_pdf_is_not_rewritten_and_changed_source_is_not_overwritten(tmp_path):
    source,output = tmp_path/"native.pdf",tmp_path/"result.pdf"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((40,80),"Native selectable text with enough characters")
        doc.save(source)
    original = source.read_bytes()
    report = prepare_ocr(source,output)
    assert not report["changed"] and not output.exists()
    commit_ocr(source,output,report,tmp_path/"backups")
    assert source.read_bytes()==original
    source.write_bytes(original+b"\n% changed externally")
    with pytest.raises(RuntimeError,match="zmieniony"):
        commit_ocr(source,output,{**report,"changed":True},tmp_path/"backups")
    assert source.read_bytes().endswith(b"changed externally")


def test_ocr_failure_does_not_touch_original(app,tmp_path,monkeypatch):
    source = tmp_path/"scan.pdf"
    create_scan(source)
    original = source.read_bytes()
    def fail(*args,**kwargs):
        raise RuntimeError("Controlled engine failure")
    monkeypatch.setattr("smart_pdf.ocr_file.page_layer",fail)
    with pytest.raises(RuntimeError,match="Controlled"):
        prepare_ocr(source,tmp_path/"result.pdf")
    assert source.read_bytes()==original


@pytest.mark.parametrize("mode",["cpu","gpu"])
def test_neural_bilingual_ocr_hybrid_correction_and_invisible_word_positions(app,tmp_path,mode):
    if not (resources()/"ppocr"/"det.onnx").exists():
        pytest.skip("PP-OCRv5 models missing")
    if mode=="gpu" and os.name!="nt":
        pytest.skip("DirectML is Windows-specific")
    source = tmp_path/"scan.pdf"
    create_scan(source)
    try:
        with pymupdf.open(source) as doc:
            data,report = page_layer(doc[0],engine=mode)
    except Exception as error:
        if mode=="gpu" and "DirectML" in str(error):
            pytest.skip("No compatible DirectML adapter")
        raise
    with pymupdf.open(stream=data,filetype="pdf") as layer:
        text = layer[0].get_text()
        assert "Dokument Smart PDF" in text
        assert "Zażółć" in text and "gęślą" in text and "jaźń" in text
        assert "quick brown fox" in text
        assert set(layer[0].get_pixmap().samples)=={255}
        word = next(w for w in layer[0].get_text("words") if w[4]=="Dokument")
        assert 45<word[0]<65 and 60<word[1]<90
    assert report["backend"]==mode
    assert report["assisted_lines"]>=1
    if mode=="gpu":
        assert all("DmlExecutionProvider" in v for v in report["providers"].values())


def test_auto_ocr_falls_back_to_cpu_when_gpu_fails(app,tmp_path,monkeypatch):
    from smart_pdf import neural_ocr
    real = neural_ocr.get_engine
    def engine(gpu):
        if gpu:
            raise RuntimeError("No GPU for this test")
        return real(False)
    monkeypatch.setattr(neural_ocr,"get_engine",engine)
    source = tmp_path/"scan.pdf"
    create_scan(source)
    with pymupdf.open(source) as doc:
        data,report = page_layer(doc[0],engine="auto")
    assert report["backend"]=="cpu" and "No GPU" in report["fallback"]
    with pymupdf.open(stream=data,filetype="pdf") as doc:
        assert "Zażółć" in doc[0].get_text()


def test_standalone_context_ocr_dialog_and_cancel_before_start(app,tmp_path):
    source = tmp_path/"kliknięty plik.pdf"
    create_scan(source)
    original = source.read_bytes()
    settings = QSettings()
    settings.setValue("ocr_engine","tesseract")
    cancelled = OCRFileDialog(source)
    cancelled.reject()
    QTest.qWait(50)
    assert cancelled.process.state()==QProcess.NotRunning
    assert source.read_bytes()==original
    cancelled.deleteLater()
    dialog = OCRFileDialog(source)
    dialog.show()
    deadline = time.monotonic()+20
    while not dialog.ocr_result and time.monotonic()<deadline:
        QTest.qWait(20)
    assert dialog.ocr_result,dialog.detail.text()
    assert dialog.ocr_result["changed"]
    assert Path(dialog.ocr_result["backup"]).read_bytes()==original
    assert "Gotowe" in dialog.label.text()
    assert dialog.temporary is None
    dialog.reject()
    dialog.deleteLater()
    settings.remove("ocr_engine")
    app.processEvents()


def test_blank_scan_is_not_rewritten(app,tmp_path):
    source,output = tmp_path/"blank.pdf",tmp_path/"result.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(source)
    original = source.read_bytes()
    report = prepare_ocr(source,output)
    assert not report["changed"] and report["words"]==0
    assert source.read_bytes()==original and not output.exists()


def test_cancel_during_ocr_keeps_source_and_removes_staging_files(app,tmp_path):
    source = tmp_path/"cancel.pdf"
    create_scan(source)
    original = source.read_bytes()
    dialog = OCRFileDialog(source)
    dialog.show()
    deadline = time.monotonic()+5
    while dialog.process.state()!=QProcess.Running and time.monotonic()<deadline:
        QTest.qWait(10)
    assert dialog.process.state()==QProcess.Running
    directory = Path(dialog.temporary.path())
    dialog.reject()
    QTest.qWait(50)
    assert dialog.process.state()==QProcess.NotRunning
    assert source.read_bytes()==original
    assert not directory.exists()
    dialog.deleteLater()
    app.processEvents()
