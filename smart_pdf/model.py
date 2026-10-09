from __future__ import annotations

import copy
import html
import json
import math
import os
import tempfile
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf

FORMAT_VERSION = 1
KINDS = {"pen", "line", "ellipse", "triangle", "rect", "text", "highlight", "underline", "strike", "replacement"}


def uid() -> str:
    return uuid.uuid4().hex


def text_html(text: str, size=14, color="#243046", bold=False, italic=False) -> str:
    weight = "bold" if bold else "normal"
    style = "italic" if italic else "normal"
    return (f'<div style="font-family:Arial;font-size:{size}pt;color:{color};'
            f'font-weight:{weight};font-style:{style}">{html.escape(text).replace(chr(10), "<br>")}</div>')


def make_object(kind: str, x=0, y=0, w=180, h=80, **kwargs) -> dict:
    if kind not in KINDS:
        raise ValueError("Nieznany typ obiektu")
    return {"id": uid(), "kind": kind, "x": x, "y": y, "w": w, "h": h,
            "rotation": 0, "color": "#2864ed", "fill": "", "width": 2,
            "opacity": 1.0, "points": [], "rects": [], "html": "", **kwargs}


@dataclass
class PageState:
    source: int
    width: float
    height: float
    id: str = field(default_factory=uid)
    rotation: int = 0
    margins: dict = field(default_factory=lambda: dict(left=0, right=0, top=0, bottom=0))
    objects: list[dict] = field(default_factory=list)

    @property
    def size(self):
        return (self.width + self.margins["left"] + self.margins["right"],
                self.height + self.margins["top"] + self.margins["bottom"])


class Project:
    def __init__(self, source_pdf: bytes, pages: list[PageState], title="Dokument"):
        self.source_pdf = source_pdf
        self.doc = pymupdf.open(stream=source_pdf, filetype="pdf")
        self.pages = pages
        self.title = title
        self.ocr: dict[int, bytes] = {}
        self.ocr_languages: dict[int, str] = {}
        self.path: Path | None = None
        self.dirty = False
        self.cache_dirty = False

    @classmethod
    def from_pdf(cls, path: str | Path, password: str = ""):
        with pymupdf.open(path) as doc:
            if doc.needs_pass and not doc.authenticate(password):
                raise PermissionError("Ten PDF wymaga prawidłowego hasła.")
            if not doc.is_pdf or not len(doc):
                raise ValueError("Dokument nie zawiera stron PDF.")
            # Freeze existing annotation/widget appearances into the original content.
            # Edits made in Smart PDF remain separate, fully editable objects.
            doc.bake(annots=True, widgets=True)
            for page in doc:
                page.remove_rotation()
            source = doc.tobytes(garbage=4, deflate=True)
            pages = [PageState(i, page.rect.width, page.rect.height) for i, page in enumerate(doc)]
        return cls(source, pages, Path(path).stem)

    @classmethod
    def blank(cls):
        with pymupdf.open() as doc:
            page = doc.new_page(width=595.276, height=841.89)
            return cls(doc.tobytes(), [PageState(0, page.rect.width, page.rect.height)], "Nowy dokument")

    def snapshot(self):
        return copy.deepcopy(self.pages)

    def restore(self, snapshot):
        self.pages = copy.deepcopy(snapshot)
        self.dirty = True

    def words(self, index):
        state = self.pages[index]
        page = self.doc[state.source]
        words = page.get_text("words", sort=True)
        if state.source in self.ocr:
            with pymupdf.open(stream=self.ocr[state.source], filetype="pdf") as odoc:
                opage = odoc[0]
                sx, sy = state.width / opage.rect.width, state.height / opage.rect.height
                words = [(w[0]*sx, w[1]*sy, w[2]*sx, w[3]*sy, *w[4:])
                         for w in opage.get_text("words", sort=True)]
        dx, dy = state.margins["left"], state.margins["top"]
        shifted = [(w[0]+dx, w[1]+dy, w[2]+dx, w[3]+dy, *w[4:]) for w in words]
        masks = [pymupdf.Rect(r) for o in state.objects for r in o.get("redactions",[])]
        return [w for w in shifted if not any(pymupdf.Rect(w[:4]).intersects(mask) for mask in masks)]

    def needs_ocr(self, source: int):
        page = self.doc[source]
        return source not in self.ocr and len(page.get_text().strip()) < 20 and bool(page.get_images() or page.get_drawings())

    def add_margin(self, indices, side, points, add_text=True):
        """Set one margin per side. Repeated additions reuse its notes object."""
        if side not in {"left", "right", "top", "bottom"} or not 10 <= points <= 1440:
            raise ValueError("Nieprawidłowy margines.")
        for index in indices:
            page = self.pages[index]
            delta = points-page.margins[side]
            dx, dy = (delta if side == "left" else 0), (delta if side == "top" else 0)
            for obj in page.objects:
                obj["x"] += dx
                obj["y"] += dy
                # Replacement masks stay fixed in page coordinates; geometry is local.
                for key in ("redactions",):
                    obj[key] = [[r[0]+dx, r[1]+dy, r[2]+dx, r[3]+dy] for r in obj.get(key, [])]
            page.margins[side] = points
            if add_text:
                notes = next((o for o in page.objects if o.get("margin_side")==side),None)
                if notes is None:
                    notes = make_object("text",html=text_html("",12),margin_side=side,
                                        rotation=-page.rotation,margin_layout_rotation=-page.rotation)
                    page.objects.append(notes)
            # Keep notes inside their own margin when either margin changes.
            for notes in page.objects:
                edge = notes.get("margin_side")
                if edge not in page.margins or not page.margins[edge]:
                    continue
                mw,mh = page.size
                if edge in {"left","right"}:
                    x = 8 if edge=="left" else mw-page.margins[edge]+8
                    x,y,w,h = x,12,page.margins[edge]-16,mh-24
                else:
                    y = 8 if edge=="top" else mh-page.margins[edge]+8
                    x,y,w,h = 12,y,mw-24,page.margins[edge]-16
                w,h = max(12,w),max(12,h)
                if notes.get("margin_layout_rotation",0)%180:
                    x,y,w,h = x+w/2-h/2,y+h/2-w/2,h,w
                notes.update(x=x,y=y,w=w,h=h)
        self.dirty = True

    def save(self, path: str | Path, autosave=False):
        path = Path(path)
        manifest = {"format": "smart-pdf", "version": FORMAT_VERSION, "title": self.title,
                    "pages": [asdict(p) for p in self.pages],
                    "ocr_languages": {str(k): v for k,v in self.ocr_languages.items()}}
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".smartpdf-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
                    archive.writestr("source.pdf", self.source_pdf)
                    for key, value in self.ocr.items():
                        archive.writestr(f"ocr/{key}.pdf", value)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        if not autosave:
            self.path, self.dirty, self.cache_dirty = path, False, False

    @classmethod
    def load(cls, path: str | Path):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or len(names) > 30000:
                raise ValueError("Nieprawidłowa struktura projektu.")
            if sum(i.file_size for i in archive.infolist()) > 2_000_000_000:
                raise ValueError("Projekt przekracza limit 2 GB.")
            if archive.getinfo("manifest.json").file_size > 30_000_000:
                raise ValueError("Opis projektu jest zbyt duży.")
            meta = json.loads(archive.read("manifest.json"))
            if meta.get("format") != "smart-pdf" or meta.get("version") != FORMAT_VERSION:
                raise ValueError("Nieobsługiwana wersja projektu Smart PDF.")
            source = archive.read("source.pdf")
            pages = [PageState(**p) for p in meta["pages"]]
            project = cls(source, pages, meta.get("title", "Dokument"))
            if not pages:
                raise ValueError("Projekt nie ma stron.")
            for page in pages:
                if not 0 <= page.source < len(project.doc) or page.rotation not in {0,90,180,270}:
                    raise ValueError("Nieprawidłowa strona projektu.")
                for number in [page.width, page.height, *page.margins.values()]:
                    if not isinstance(number, (int,float)) or not math.isfinite(number) or not 0 <= number <= 20000:
                        raise ValueError("Nieprawidłowy rozmiar strony.")
                if set(page.margins) != {"left", "right", "top", "bottom"}:
                    raise ValueError("Nieprawidłowe marginesy.")
                if page.width <= 0 or page.height <= 0:
                    raise ValueError("Strona musi mieć dodatni rozmiar.")
                for obj in page.objects:
                    if obj.get("kind") not in KINDS:
                        raise ValueError("Nieznany obiekt projektu.")
                    for key in ("x", "y", "w", "h", "rotation", "width", "opacity"):
                        val = obj.get(key, 0)
                        if not isinstance(val, (int,float)) or not math.isfinite(val) or abs(val) > 1_000_000:
                            raise ValueError("Nieprawidłowe dane obiektu.")
                    if obj["w"] <= 0 or obj["h"] <= 0 or not 0 <= obj["opacity"] <= 1:
                        raise ValueError("Nieprawidłowy rozmiar/przezroczystość obiektu.")
            for name in names:
                if name.startswith("ocr/") and name.endswith(".pdf"):
                    index = int(Path(name).stem)
                    if not 0 <= index < len(project.doc):
                        raise ValueError("Nieprawidłowa strona OCR.")
                    value = archive.read(name)
                    with pymupdf.open(stream=value, filetype="pdf") as ocr_doc:
                        if len(ocr_doc) != 1:
                            raise ValueError("Nieprawidłowy wynik OCR.")
                    project.ocr[index] = value
            project.ocr_languages = {int(k):v for k,v in meta.get("ocr_languages", {}).items()}
        project.path = Path(path)
        return project
