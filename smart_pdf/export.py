"""Preserve original vectors/text and draw editable objects as a PDF overlay."""
import os
import tempfile
from pathlib import Path

import pymupdf
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter

from smart_pdf.painting import paint_object


def overlay_pdf(state):
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    writer = QPdfWriter(buffer)
    writer.setResolution(72)
    writer.setPageSize(QPageSize(QSizeF(*state.size), QPageSize.Point))
    writer.setPageMargins(QMarginsF(0,0,0,0), QPageLayout.Point)
    writer.setTitle("Smart PDF - obiekty")
    painter = QPainter(writer)
    if not painter.isActive():
        raise RuntimeError("Nie można utworzyć warstwy PDF.")
    painter.setRenderHint(QPainter.Antialiasing)
    for obj in state.objects:
        painter.save()
        painter.translate(obj["x"]+obj["w"]/2,obj["y"]+obj["h"]/2)
        painter.rotate(obj["rotation"])
        painter.translate(-obj["w"]/2,-obj["h"]/2)
        paint_object(painter,obj)
        painter.restore()
    painter.end()
    # QPdfWriter must finalize the stream before it is read.
    del writer
    buffer.close()
    return bytes(data)


def export_pdf(project, path):
    output = pymupdf.open()
    try:
        for state in project.pages:
            base = pymupdf.open()
            base.insert_pdf(project.doc, from_page=state.source, to_page=state.source)
            dx,dy = state.margins["left"],state.margins["top"]
            redactions = [pymupdf.Rect(r)-pymupdf.Rect(dx,dy,dx,dy)
                          for obj in state.objects for r in obj.get("redactions", [])]
            # Remove the original text/pixels instead of hiding it under a white box.
            for rect in redactions:
                base[0].add_redact_annot(rect, fill=(1,1,1))
            if redactions:
                base[0].apply_redactions(images=2, graphics=0, text=0)
            page = output.new_page(width=state.size[0],height=state.size[1])
            target = pymupdf.Rect(dx,dy,dx+state.width,dy+state.height)
            if base[0].get_contents():
                page.show_pdf_page(target, base, 0)
            base.close()
            if state.source in project.ocr:
                with pymupdf.open(stream=project.ocr[state.source],filetype="pdf") as odoc:
                    op = odoc[0]
                    # Keep the invisible OCR text, preserve the original image quality.
                    for image in op.get_images():
                        op.delete_image(image[0])
                    sx,sy = op.rect.width/state.width,op.rect.height/state.height
                    for rect in redactions:
                        op.add_redact_annot(pymupdf.Rect(rect.x0*sx,rect.y0*sy,rect.x1*sx,rect.y1*sy))
                    if redactions:
                        op.apply_redactions(images=0,graphics=0,text=0)
                    page.show_pdf_page(target,odoc,0)
            if state.objects:
                with pymupdf.open(stream=overlay_pdf(state),filetype="pdf") as overlay:
                    page.show_pdf_page(page.rect,overlay,0)
            page.set_rotation(state.rotation)
        output.set_metadata({"title":project.title,"creator":"Smart PDF","producer":"Smart PDF / MuPDF / Qt"})
        path = Path(path)
        fd,tmp = tempfile.mkstemp(prefix=".smartpdf-export-",suffix=".pdf",dir=path.parent)
        os.close(fd)
        try:
            output.save(tmp,garbage=4,deflate=True)
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    finally:
        output.close()
