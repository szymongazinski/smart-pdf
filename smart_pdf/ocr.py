"""OCR executes in a child process; MuPDF is never shared between threads."""
from pathlib import Path
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


def run_worker(source, output, index, languages, dpi=300, rotation=0):
    os.environ["OMP_THREAD_LIMIT"] = "2"
    import pymupdf
    with pymupdf.open(source) as doc:
        page = doc[int(index)]
        rotation = int(rotation)%360
        if rotation not in {0,90,180,270}:
            raise ValueError("Nieprawidłowy obrót OCR")
        page.set_rotation(rotation)
        # Bound memory even for oversized posters.
        area = page.rect.width * page.rect.height
        dpi = min(int(dpi), max(72, int(72 * (24_000_000 / max(area,1)) ** .5)))
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
        data = pixmap.pdfocr_tobytes(language=languages, tessdata=str(tessdata()))
        if rotation:
            with pymupdf.open(stream=data,filetype="pdf") as result:
                result[0].set_rotation((-rotation)%360)
                result[0].remove_rotation()
                data = result.tobytes(garbage=4,deflate=True)
        temporary = Path(output).with_suffix(".partial")
        temporary.write_bytes(data)
        temporary.replace(output)
