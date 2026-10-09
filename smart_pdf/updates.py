"""Explicit, verified updates from this project's GitHub releases."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QThread, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from smart_pdf import __version__

RELEASES = "https://api.github.com/repos/szymongazinski/smart-pdf/releases?per_page=20"
DOWNLOAD_PREFIX = "https://github.com/szymongazinski/smart-pdf/releases/download/"


def version_key(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)",value)
    return tuple(map(int,match.groups())) if match else (0,0,0)


def choose_update(releases,current):
    candidates = []
    for release in releases:
        if release.get("draft") or version_key(release.get("tag_name",""))<=version_key(current):
            continue
        for asset in release.get("assets",[]):
            name = asset.get("name","")
            digest = asset.get("digest","")
            url = asset.get("browser_download_url","")
            if (name.startswith("SmartPDF-Update-") and name.endswith("-x64.exe")
                    and re.fullmatch(r"sha256:[0-9a-f]{64}",digest) and url.startswith(DOWNLOAD_PREFIX)):
                candidates.append((version_key(release["tag_name"]),{"version":release["tag_name"].lstrip("v"),"name":name,"url":url,"sha256":digest[7:],"size":asset.get("size",0),"notes":release.get("body","")}))
    return max(candidates,key=lambda p:p[0])[1] if candidates else None


def request(url):
    return urllib.request.Request(url,headers={"User-Agent":f"SmartPDF/{__version__}","Accept":"application/vnd.github+json" if url==RELEASES else "application/octet-stream"})


def download_verified(info,directory,progress=lambda *args:None,cancelled=lambda:False):
    if not info["url"].startswith(DOWNLOAD_PREFIX) or not re.fullmatch(r"[0-9a-f]{64}",info["sha256"]):
        raise ValueError("Nieprawidłowe źródło aktualizacji.")
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    target = directory/Path(info["name"]).name
    fd,temporary = tempfile.mkstemp(prefix="download-",suffix=".part",dir=directory)
    try:
        digest,total = hashlib.sha256(),0
        with os.fdopen(fd,"wb") as stream,urllib.request.urlopen(request(info["url"]),timeout=30) as response:
            while chunk:=response.read(256*1024):
                if cancelled():
                    raise InterruptedError("Pobieranie anulowane.")
                total += len(chunk)
                if total>400*1024*1024:
                    raise ValueError("Aktualizacja przekracza limit rozmiaru.")
                stream.write(chunk)
                digest.update(chunk)
                progress(total,info.get("size",0))
            stream.flush()
            os.fsync(stream.fileno())
        if digest.hexdigest()!=info["sha256"] or info.get("size") and total!=info["size"]:
            raise ValueError("Suma kontrolna aktualizacji jest niezgodna. Plik nie zostanie uruchomiony.")
        os.replace(temporary,target)
        return str(target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class UpdateWorker(QThread):
    checked = Signal(object)
    downloaded = Signal(str)
    failed = Signal(str)
    progress = Signal(int,int)

    def __init__(self,info=None,parent=None):
        super().__init__(parent)
        self.info = info

    def run(self):
        try:
            if self.info:
                directory = Path(QStandardPaths.writableLocation(QStandardPaths.CacheLocation))/"updates"
                path = download_verified(self.info,directory,self.progress.emit,self.isInterruptionRequested)
                self.downloaded.emit(path)
            else:
                with urllib.request.urlopen(request(RELEASES),timeout=20) as response:
                    releases = json.loads(response.read(2_000_000))
                self.checked.emit(choose_update(releases,__version__))
        except Exception as error:
            self.failed.emit(str(error))


class UpdateDialog(QDialog):
    def __init__(self,window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Aktualizacje Smart PDF")
        self.resize(490,240)
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Zainstalowana wersja: {__version__}\nSprawdzanie wydań na GitHub…")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.progress = QProgressBar()
        self.progress.setRange(0,0)
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        row.addStretch()
        self.install = QPushButton("Pobierz i aktualizuj")
        self.install.setObjectName("primary")
        self.install.setEnabled(False)
        self.install.clicked.connect(self.download)
        row.addWidget(self.install)
        self.close_button = QPushButton("Zamknij")
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        layout.addLayout(row)
        self.worker = None
        self.start_worker(UpdateWorker(parent=self))

    def start_worker(self,worker):
        self.worker = worker
        worker.checked.connect(self.checked)
        worker.downloaded.connect(self.apply)
        worker.failed.connect(self.failed)
        worker.progress.connect(self.update_progress)
        worker.start()

    def checked(self,info):
        self.progress.hide()
        self.info = info
        if info:
            self.label.setText(f"Dostępna wersja: {info['version']}\n\nAktualizacja podmieni pliki programu i zachowa ustawienia oraz projekty. Program zostanie zamknięty i uruchomiony ponownie.")
            self.install.setEnabled(True)
        else:
            self.label.setText(f"Masz aktualną wersję Smart PDF ({__version__}).")

    def download(self):
        if not getattr(__import__("sys"),"frozen",False):
            self.label.setText("Aktualizator służy do wersji zainstalowanej. Kopię ze źródeł zaktualizuj przez Git.")
            return
        self.install.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0,100)
        self.label.setText("Pobieranie aktualizacji…")
        self.start_worker(UpdateWorker(self.info,self))

    def update_progress(self,received,total):
        self.progress.setValue(round(received/total*100) if total else 0)

    def failed(self,message):
        self.progress.hide()
        self.label.setText("Nie udało się zaktualizować:\n"+message)
        self.install.setEnabled(bool(getattr(self,"info",None)))

    def apply(self,path):
        if not self.window.maybe_save():
            self.label.setText("Aktualizacja pobrana. Zapisz projekt i kliknij ponownie, aby kontynuować.")
            self.install.setEnabled(True)
            return
        try:
            subprocess.Popen([path,"/SP-"],close_fds=True)
        except OSError as error:
            self.failed(str(error))
            return
        self.accept()
        self.window.close()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.label.setText("Kończenie pobierania…")
            self.close_button.setEnabled(False)
            self.worker.finished.connect(super().reject)
            return
        super().reject()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
