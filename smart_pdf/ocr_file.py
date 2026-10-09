"""Prepare OCR without touching the source; validate before atomic replacement."""
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

import pymupdf

from smart_pdf.ocr import page_layer


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk:=stream.read(1024*1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_report(path,value):
    path = Path(path)
    temporary = path.with_suffix(".partial")
    temporary.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
    os.replace(temporary,path)


def prepare_ocr(source,output,languages="pol+eng",dpi=300,engine="auto",password="",progress=lambda v:None):
    source,output = Path(source),Path(output)
    if source.resolve()==output.resolve():
        raise ValueError("Wynik roboczy musi być oddzielony od oryginału.")
    if source.suffix.lower()!=".pdf":
        raise ValueError("Wybierz plik PDF.")
    original_hash = file_hash(source)
    report = {"source":str(source),"source_sha256":original_hash,"pages_done":0,
              "pages_skipped":0,"words":0,"assisted_lines":0,"backends":[],"changed":False}
    with pymupdf.open(source) as doc:
        if not doc.is_pdf or not len(doc):
            raise ValueError("Dokument nie zawiera stron PDF.")
        if doc.needs_pass and not doc.authenticate(password):
            raise PermissionError("Nieprawidłowe hasło PDF.")
        report["pages"] = len(doc)
        for index,page in enumerate(doc):
            progress({**report,"page":index+1,"message":"Rozpoznawanie tekstu…"})
            # Native/searchable pages retain their existing, more precise text.
            if len(page.get_text().strip())>=20:
                report["pages_skipped"] += 1
                continue
            data,info = page_layer(page,languages,dpi,engine=engine)
            if info["words"]:
                with pymupdf.open(stream=data,filetype="pdf") as layer:
                    target = pymupdf.Rect(0,0,page.cropbox.width,page.cropbox.height)
                    # MuPDF's transformation matrix for a rotated cropped page
                    # omits the crop offset. Insert in unrotated coordinates.
                    rotation = page.rotation
                    try:
                        page.set_rotation(0)
                        page.show_pdf_page(target,layer,0,overlay=True)
                    finally:
                        page.set_rotation(rotation)
                report["changed"] = True
                report["words"] += info["words"]
            report["pages_done"] += 1
            report["assisted_lines"] += info["assisted_lines"]
            if info["backend"] not in report["backends"]:
                report["backends"].append(info["backend"])
            if info.get("fallback"):
                report["fallback"] = info["fallback"]
            progress({**report,"page":index+1,"message":"Strona rozpoznana"})
        if report["changed"]:
            doc.save(output,garbage=4,deflate=True,encryption=pymupdf.PDF_ENCRYPT_KEEP)
    if report["changed"]:
        with pymupdf.open(output) as checked:
            if checked.needs_pass and not checked.authenticate(password):
                raise ValueError("Nie udało się sprawdzić zaszyfrowanego wyniku OCR.")
            if len(checked)!=report["pages"]:
                raise ValueError("Wynik OCR ma nieprawidłową liczbę stron.")
    return report


def commit_ocr(source,output,report,backup_directory):
    """Back up the exact input and reject files changed while OCR was running."""
    source,output = Path(source),Path(output)
    if file_hash(source)!=report["source_sha256"]:
        raise RuntimeError("PDF został zmieniony podczas OCR. Oryginał nie został podmieniony.")
    if not report["changed"]:
        return {**report,"backup":""}
    before = source.stat()
    backup = Path(backup_directory)/uuid.uuid4().hex/source.name
    backup.parent.mkdir(parents=True,exist_ok=False)
    try:
        shutil.copy2(source,backup)
        if file_hash(backup)!=report["source_sha256"] or source.stat().st_mtime_ns!=before.st_mtime_ns:
            raise RuntimeError("PDF został zmieniony podczas zapisu. Nie został podmieniony.")
        os.chmod(output,before.st_mode)
        os.replace(output,source)
    except Exception:
        # A complete backup remains recoverable even if the final rename fails.
        raise
    return {**report,"backup":str(backup)}


def run_file_worker(job_path):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    report_path = Path(job["report"])
    try:
        report = prepare_ocr(job["source"],job["output"],job["languages"],job["dpi"],
                             job["engine"],job.get("password",""),
                             lambda v:write_report(report_path,{**v,"state":"working"}))
        write_report(report_path,{**report,"state":"prepared"})
        return 0
    except Exception as error:
        write_report(report_path,{"state":"error","error":str(error)})
        return 1
