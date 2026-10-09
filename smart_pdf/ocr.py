"""OCR executes in a child process; MuPDF is never shared between threads."""
from pathlib import Path
import json
import os
import sys


def resources():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / "assets"


def tessdata():
    override = os.environ.get("SMARTPDF_TESSDATA")
    return Path(override) if override else resources() / "tessdata"


def available_languages():
    return sorted(p.stem for p in tessdata().glob("*.traineddata"))


ENGINE_OPTIONS = [("auto","GPU jeśli dostępne (zalecane)"),
                  ("cpu","Tylko CPU — PP-OCRv5"),
                  ("gpu","GPU — DirectML"),
                  ("tesseract","CPU — Tesseract LSTM")]


def page_layer(page,languages="pol+eng",dpi=300,rotation=None,engine="auto"):
    os.environ["OMP_THREAD_LIMIT"] = "2"
    import pymupdf
    original_rotation = page.rotation
    rotation = original_rotation if rotation is None else int(rotation)%360
    if rotation not in {0,90,180,270}:
        raise ValueError("Nieprawidłowy obrót OCR")
    try:
        page.set_rotation(rotation)
        area = page.rect.width*page.rect.height
        dpi = min(int(dpi),max(72,int(72*(24_000_000/max(area,1))**.5)))
        pixmap = page.get_pixmap(dpi=dpi,colorspace=pymupdf.csRGB,alpha=False)
        if engine=="tesseract":
            data = pixmap.pdfocr_tobytes(language=languages,tessdata=str(tessdata()))
            report = {"backend":"tesseract","assisted_lines":0}
        else:
            from smart_pdf.neural_ocr import make_layer
            data,report = make_layer(pixmap,languages,engine,page.rect.width,page.rect.height)
        if rotation:
            with pymupdf.open(stream=data,filetype="pdf") as result:
                result[0].set_rotation((-rotation)%360)
                result[0].remove_rotation()
                data = result.tobytes(garbage=4,deflate=True)
        # Remove the temporary raster from the classic OCR output too.
        with pymupdf.open(stream=data,filetype="pdf") as result:
            for image in result[0].get_images():
                result[0].delete_image(image[0])
            report["words"] = len(result[0].get_text("words"))
            return result.tobytes(garbage=4,deflate=True),report
    finally:
        page.set_rotation(original_rotation)


def run_worker(source, output, index, languages, dpi=300, rotation=0,engine="auto"):
    import pymupdf
    with pymupdf.open(source) as doc:
        data,report = page_layer(doc[int(index)],languages,dpi,rotation,engine)
        temporary = Path(output).with_suffix(".partial")
        temporary.write_bytes(data)
        temporary.replace(output)
        Path(str(output)+".json").write_text(json.dumps(report),encoding="utf-8")
