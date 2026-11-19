import pymupdf
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from smart_pdf import page_ranges
from smart_pdf.dialogs import CutPagesDialog
from smart_pdf.export import export_pdf
from smart_pdf.model import Project, make_object, text_html
from smart_pdf.window import MainWindow
from test_ui import finish


@pytest.mark.parametrize('text,count,want',[
    ('11-19 i 20-35',40,list(range(10,35))),
    ('11mamwielkiegochuja i nie mieści sięwspodniach-14',20,[10,11,12,13]),
    ('3, 1 i 3; 2-4',5,[0,1,2,3]),
    ('strony 11 słowa 14',20,[10,13]),
    ('1–3; 5—6; 8−9',9,[0,1,2,4,5,7,8]),
    ('1-1',1,[0]),
])
def test_ranges_ignore_words_without_joining_separate_numbers(text,count,want):
    assert page_ranges.parse_page_ranges(text,count)==want


@pytest.mark.parametrize('text',['','bez liczb','0','6','5-2','1-','-2','1--3','1-3-5','1-9999999999999999999999'])
def test_invalid_ranges_are_rejected(text):
    with pytest.raises(ValueError):
        page_ranges.parse_page_ranges(text,5)


def test_keep_remove_and_nonempty_result():
    assert page_ranges.remaining_pages('2-4',6,'keep')==[1,2,3]
    assert page_ranges.remaining_pages('2-4',6,'remove')==[0,4,5]
    with pytest.raises(ValueError):
        page_ranges.remaining_pages('1-6',6,'remove')
    with pytest.raises(ValueError):
        page_ranges.remaining_pages('2',6,'unknown')


def test_dialog_previews_both_modes_and_blocks_empty_result(app):
    dialog=CutPagesDialog(6)
    assert not dialog.apply_button.isEnabled()
    dialog.ranges.setText('2 abc-4')
    assert dialog.indices()==[1,2,3]
    assert dialog.apply_button.isEnabled()
    assert '2-4' in dialog.preview.text()
    dialog.remove.setChecked(True)
    assert dialog.indices()==[0,4,5]
    dialog.ranges.setText('1-6')
    assert not dialog.apply_button.isEnabled()
    dialog.ranges.setText('6')
    assert dialog.indices()==[0,1,2,3,4]
    dialog.deleteLater()


@pytest.mark.parametrize('mode,want',[('keep',[1,2,3]),('remove',[0,4,5])])
def test_page_selection_preserves_objects_undo_redo_and_saved_outputs(app,tmp_path,mode,want):
    source=tmp_path/'source.pdf'
    with pymupdf.open() as doc:
        for i in range(6):
            doc.new_page().insert_text((40,60),f'Original page {i+1}')
        doc.save(source)
    original=source.read_bytes()
    window=MainWindow()
    project=Project.from_pdf(source)
    for i,p in enumerate(project.pages):
        p.rotation=(i%4)*90
        p.margins['right']=30+i
        p.objects.append(make_object('text',40,100,180,40,html=text_html(f'Note {i+1}')))
    before=project.snapshot()
    window.attach_project(project)
    window.change_page(5)
    window.apply_page_selection('2-4',mode)
    assert [p.source for p in project.pages]==want
    assert 0<=window.index<3
    assert project.pages==[before[i] for i in want]
    window.undo.undo()
    assert project.pages==before
    window.undo.redo()
    assert [p.source for p in project.pages]==want
    project.save(tmp_path/'trimmed.smartpdf')
    loaded=Project.load(tmp_path/'trimmed.smartpdf')
    assert loaded.pages==project.pages
    export_pdf(loaded,tmp_path/'trimmed.pdf')
    with pymupdf.open(tmp_path/'trimmed.pdf') as result:
        assert len(result)==3
        for out,index in zip(result,want):
            assert f'Original page {index+1}' in out.get_text()
            assert f'Note {index+1}' in out.get_text()
    assert source.read_bytes()==original
    loaded.doc.close()
    finish(window,app)
