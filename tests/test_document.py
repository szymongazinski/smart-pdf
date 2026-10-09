import json
import zipfile

import pymupdf
import pytest

from smart_pdf.export import export_pdf,overlay_pdf
from smart_pdf.model import PageState,Project,make_object,text_html
from smart_pdf.ocr import available_languages,run_worker


def source_project(tmp_path,rotation=0):
    path = tmp_path/"source.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=400,height=500)
        page.insert_text((40,80),"Original confidential token",fontsize=16)
        page.insert_text((40,130),"Other paragraph stays intact",fontsize=14)
        page.set_rotation(rotation)
        doc.save(path)
    return Project.from_pdf(path)


def test_project_roundtrip_keeps_original_objects_and_ocr(tmp_path,app):
    project = source_project(tmp_path)
    obj = make_object("text",10,220,250,80,html=text_html("Zażółć gęślą jaźń",16,"#ef4d64",True,True),rotation=32)
    project.pages[0].objects.append(obj)
    project.add_margin([0],"left",100)
    path = tmp_path/"edit.smartpdf"
    project.save(path)
    restored = Project.load(path)
    assert restored.source_pdf == project.source_pdf
    assert restored.pages == project.pages
    assert restored.pages[0].objects[0]["rotation"] == 32
    assert restored.pages[0].objects[0]["x"] == 110
    assert "Original" in restored.doc[0].get_text()
    assert not restored.dirty


def test_export_preserves_native_text_and_unicode_rich_text(tmp_path,app):
    project = source_project(tmp_path)
    project.pages[0].objects.append(make_object("text",20,210,340,100,html=text_html("Zażółć gęślą jaźń",18,"#ef4d64",True,True)))
    project.add_margin([0],"right",120)
    project.pages[0].rotation = 90
    target = tmp_path/"export.pdf"
    export_pdf(project,target)
    with pymupdf.open(target) as result:
        page = result[0]
        text = page.get_text()
        assert "Original confidential token" in text
        assert "Zażółć gęślą jaźń" in text
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b for l in b["lines"] for s in l["spans"]]
        added = next(s for s in spans if "Zażółć" in s["text"])
        assert abs(added["size"]-18)<.1
        assert "Kliknij, aby" not in text  # Empty notes show a UI-only placeholder.
        assert page.rotation == 90
        assert page.rect.width == 500
        assert page.rect.height == 520
        assert page.get_pixmap().width == 500
        assert "Original" in project.doc[0].get_text()


def test_replacement_removes_original_in_export_and_is_reversible(tmp_path,app):
    project = source_project(tmp_path)
    rects = [list(r) for r in project.doc[0].search_for("confidential token")]
    project.pages[0].objects.append(make_object("replacement",110,60,230,60,html=text_html("public information",14),redactions=rects))
    project.add_margin([0],"left",80,False)
    path = tmp_path/"redacted.pdf"
    export_pdf(project,path)
    with pymupdf.open(path) as doc:
        assert "confidential" not in doc[0].get_text()
        assert "token" not in doc[0].get_text()
        assert "public information" in doc[0].get_text()
        assert "Other paragraph" in doc[0].get_text()
    assert "confidential token" in project.doc[0].get_text()
    assert "confidential" not in " ".join(w[4] for w in project.words(0))
    snapshot = project.snapshot()
    project.pages[0].objects.clear()
    project.restore(snapshot)
    assert len(project.pages[0].objects) == 1


@pytest.mark.parametrize("side",["left","right","top","bottom"])
def test_margins_shift_objects_and_fixed_masks_consistently(tmp_path,side):
    project = source_project(tmp_path)
    obj = make_object("replacement",10,20,100,30,redactions=[[10,20,40,30]])
    project.pages[0].objects.append(obj)
    project.add_margin([0],side,50)
    assert obj["x"] == 10+(50 if side=="left" else 0)
    assert obj["y"] == 20+(50 if side=="top" else 0)
    assert obj["redactions"][0][0] == obj["x"]
    assert obj["redactions"][0][1] == obj["y"]
    assert len(project.pages[0].objects) == 2


def test_input_rotation_is_normalized_without_losing_text(tmp_path,app):
    project = source_project(tmp_path,90)
    assert project.pages[0].size == (500,400)
    assert project.doc[0].rotation == 0
    assert "Original" in project.doc[0].get_text()
    export_pdf(project,tmp_path/"normalized.pdf")
    with pymupdf.open(tmp_path/"normalized.pdf") as result:
        assert result[0].rect == project.doc[0].rect
        assert "Original" in result[0].get_text()


def test_shapes_and_freehand_export_as_vectors(tmp_path,app):
    project = Project.blank()
    for i,kind in enumerate(["line","ellipse","triangle","rect","pen","highlight","underline"]):
        obj = make_object(kind,30,30+i*80,120,45,color="#ef4d64",fill="#dfeaff" if kind=="triangle" else "",points=[[0,0],[.5,1],[1,0]],rects=[[0,0,1,1]],opacity=.35 if kind=="highlight" else 1)
        project.pages[0].objects.append(obj)
    export_pdf(project,tmp_path/"shapes.pdf")
    with pymupdf.open(tmp_path/"shapes.pdf") as doc:
        assert len(doc[0].get_drawings())>=7
        assert not doc[0].get_images()


def test_reorder_and_rotation_are_exported(tmp_path,app):
    with pymupdf.open() as doc:
        for value in ["First","Second","Third"]:
            doc.new_page(width=300,height=400).insert_text((20,30),value)
        source = doc.tobytes()
    project = Project(source,[PageState(i,300,400) for i in [2,0,1]])
    project.pages[1].rotation = 180
    export_pdf(project,tmp_path/"ordered.pdf")
    with pymupdf.open(tmp_path/"ordered.pdf") as doc:
        assert [p.get_text().strip() for p in doc]==["Third","First","Second"]
        assert doc[1].rotation==180


def test_atomic_project_save_preserves_previous_file_on_failure(tmp_path,monkeypatch):
    project = Project.blank()
    path = tmp_path/"project.smartpdf"
    project.save(path)
    original = path.read_bytes()
    import smart_pdf.model as model
    def fail(*args):
        raise PermissionError("file locked")
    monkeypatch.setattr(model.os,"replace",fail)
    with pytest.raises(PermissionError):
        project.save(path)
    assert path.read_bytes()==original
    assert not list(tmp_path.glob(".smartpdf-*"))


def test_future_format_rejected(tmp_path):
    path = tmp_path/"bad.smartpdf"
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("manifest.json",json.dumps({"format":"smart-pdf","version":999}))
    with pytest.raises(ValueError,match="wersja"):
        Project.load(path)


@pytest.mark.skipif(not {"pol","eng"}<=set(available_languages()),reason="Download OCR models with scripts/fetch_ocr.py")
def test_real_bilingual_ocr_searchable_export_and_project_roundtrip(tmp_path,app):
    project = Project.blank()
    state = project.pages[0]
    state.objects.append(make_object("text",45,60,490,150,html=text_html("Dokument Smart PDF\nPolski tekst: Zażółć gęślą jaźń.\nEnglish text: The quick brown fox.",22,"#111111")))
    vector = overlay_pdf(state)
    with pymupdf.open(stream=vector,filetype="pdf") as doc:
        pix = doc[0].get_pixmap(dpi=200,alpha=False)
    with pymupdf.open() as scan:
        page = scan.new_page(width=state.width,height=state.height)
        page.insert_image(page.rect,stream=pix.tobytes("png"))
        scan.save(tmp_path/"scan.pdf")
    project = Project.from_pdf(tmp_path/"scan.pdf")
    assert project.needs_ocr(0)
    Path = __import__("pathlib").Path
    Path(tmp_path/"normalized.pdf").write_bytes(project.source_pdf)
    run_worker(str(tmp_path/"normalized.pdf"),str(tmp_path/"ocr.pdf"),0,"pol+eng",300)
    project.ocr[0] = Path(tmp_path/"ocr.pdf").read_bytes()
    project.ocr_languages[0] = "pol+eng"
    recognized = " ".join(w[4] for w in project.words(0))
    assert "Dokument Smart PDF" in recognized
    assert "quick brown fox" in recognized
    assert "Zażółć" in recognized
    project.add_margin([0],"left",80)
    export_pdf(project,tmp_path/"ocr-export.pdf")
    with pymupdf.open(tmp_path/"ocr-export.pdf") as result:
        assert "Dokument Smart PDF" in result[0].get_text()
        assert "quick brown fox" in result[0].get_text()
        words = result[0].get_text("words")
        first = next(w for w in words if w[4]=="Dokument")
        assert first[0]>100
        assert result[0].get_pixmap().width>650
    project.save(tmp_path/"ocr.smartpdf")
    restored = Project.load(tmp_path/"ocr.smartpdf")
    assert restored.ocr == project.ocr
    assert restored.ocr_languages[0]=="pol+eng"
    word = next(w for w in project.words(0) if w[4]=="brown")
    project.pages[0].objects.append(make_object("replacement",word[0],word[1],120,45,html=text_html("green",16),redactions=[list(word[:4])]))
    export_pdf(project,tmp_path/"ocr-replacement.pdf")
    with pymupdf.open(tmp_path/"ocr-replacement.pdf") as result:
        assert "brown" not in result[0].get_text()
        assert "green" in result[0].get_text()


def test_saved_text_style_and_rotation_export_beyond_one_session(tmp_path,app):
    project = Project.blank()
    project.pages[0].objects.append(make_object("text",140,200,220,90,rotation=35,html=text_html("Rotated bold italic",17,"#ef4d64",True,True)))
    project.save(tmp_path/"styled.smartpdf")
    restored = Project.load(tmp_path/"styled.smartpdf")
    export_pdf(restored,tmp_path/"styled.pdf")
    with pymupdf.open(tmp_path/"styled.pdf") as doc:
        lines = [l for b in doc[0].get_text("dict")["blocks"] if "lines" in b for l in b["lines"]]
        span = next(s for l in lines for s in l["spans"] if "Rotated" in s["text"])
        assert span["flags"] & 2 # italic
        assert span["flags"] & 16 # bold
        assert span["color"] == 0xef4d64
        assert any(abs(line["dir"][1])>.4 for line in lines)
