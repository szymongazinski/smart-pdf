"""A standalone OCR window launched from Explorer, without opening the editor."""
import json
import sys
from pathlib import Path

import pymupdf
from PySide6.QtCore import QProcess,QSettings,QStandardPaths,QTemporaryDir,QTimer,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog,QHBoxLayout,QInputDialog,QLabel,QLineEdit,QProgressBar,QPushButton,QVBoxLayout

from smart_pdf.ocr_file import commit_ocr
from smart_pdf.style import STYLE


class OCRFileDialog(QDialog):
    def __init__(self,path):
        super().__init__()
        self.path = Path(path).resolve()
        self.setWindowTitle("Smart PDF — wykonaj OCR")
        self.setStyleSheet(STYLE)
        self.resize(560,290)
        self.cancelled = False
        self.temporary = None
        self.job_temporary = None
        self.ocr_result = None
        layout = QVBoxLayout(self)
        heading = QLabel(self.path.name)
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size:18px;font-weight:600;padding:8px 0")
        layout.addWidget(heading)
        self.label = QLabel("Przygotowanie lokalnego OCR…")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.progress = QProgressBar()
        self.progress.setRange(0,0)
        layout.addWidget(self.progress)
        self.detail = QLabel("Po ukończeniu wynik zastąpi ten PDF. Kopia oryginału zostanie zachowana lokalnie.")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        row = QHBoxLayout()
        self.open_button = QPushButton("Otwórz PDF")
        self.open_button.hide()
        self.open_button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path))))
        row.addWidget(self.open_button)
        self.backup_button = QPushButton("Kopia oryginału")
        self.backup_button.hide()
        self.backup_button.clicked.connect(self.open_backup)
        row.addWidget(self.backup_button)
        row.addStretch()
        self.cancel_button = QPushButton("Anuluj")
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.process = QProcess(self)
        self.process.finished.connect(self.worker_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.read_progress)
        QTimer.singleShot(0,self.start)

    def start(self):
        if self.cancelled:
            return
        try:
            if not self.path.is_file() or self.path.suffix.lower()!=".pdf":
                raise ValueError("Nie znaleziono pliku PDF.")
            password = ""
            with pymupdf.open(self.path) as doc:
                if doc.needs_pass:
                    password,ok = QInputDialog.getText(self,"Hasło PDF","Podaj hasło do PDF:",QLineEdit.Password)
                    if not ok:
                        self.reject()
                        return
                    if not doc.authenticate(password):
                        raise PermissionError("Nieprawidłowe hasło PDF.")
            self.temporary = QTemporaryDir(str(self.path.parent/".smartpdf-ocr-XXXXXX"))
            if not self.temporary.isValid():
                raise PermissionError("Brak uprawnień do zapisu w folderze PDF.")
            directory = Path(self.temporary.path())
            # Keep a PDF password in the user's private temp directory, even
            # when the selected PDF is in a shared/network folder.
            self.job_temporary = QTemporaryDir()
            if not self.job_temporary.isValid():
                raise PermissionError("Nie można przygotować prywatnego katalogu OCR.")
            self.report_path = directory/"report.json"
            self.output = directory/"result.pdf"
            settings = QSettings()
            job = {"source":str(self.path),"output":str(self.output),"report":str(self.report_path),
                   "languages":settings.value("ocr_languages","pol+eng"),
                   "dpi":settings.value("ocr_dpi",300,type=int),
                   "engine":settings.value("ocr_engine","auto"),"password":password}
            job_path = Path(self.job_temporary.path())/"job.json"
            job_path.write_text(json.dumps(job),encoding="utf-8")
            args = ["--ocr-file-worker",str(job_path)]
            if not getattr(sys,"frozen",False):
                args = ["-m","smart_pdf",*args]
            self.process.start(sys.executable,args)
            self.timer.start()
        except Exception as error:
            self.failed(str(error))

    def read_progress(self):
        if not hasattr(self,"report_path") or not self.report_path.exists():
            return
        try:
            value = json.loads(self.report_path.read_text(encoding="utf-8"))
            if value.get("state")=="working":
                page,total = value["page"],value["pages"]
                self.progress.setRange(0,total)
                self.progress.setValue(page-1)
                backend = "GPU — DirectML" if "gpu" in value["backends"] else "Lokalny OCR"
                self.label.setText(f"{backend} • strona {page} z {total}\n{value['message']}")
        except (OSError,ValueError,KeyError):
            pass

    def worker_finished(self,code,status):
        self.timer.stop()
        if self.cancelled:
            self.cleanup()
            return
        try:
            value = json.loads(self.report_path.read_text(encoding="utf-8"))
            if code!=0 or value.get("state")!="prepared":
                raise RuntimeError(value.get("error","OCR nie zakończył się poprawnie."))
            backups = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))/"OCR backups"
            self.ocr_result = commit_ocr(self.path,self.output,value,backups)
            self.progress.setRange(0,100)
            self.progress.setValue(100)
            if self.ocr_result["changed"]:
                backend = "GPU — DirectML" if "gpu" in self.ocr_result["backends"] else "CPU"
                self.label.setText(f"Gotowe — PDF został podmieniony.\n{backend} • rozpoznano {self.ocr_result['pages_done']} stron.")
            else:
                self.label.setText("PDF ma już warstwę tekstu. Plik pozostawiono bez zmian."
                                   if self.ocr_result["pages_skipped"]==self.ocr_result["pages"] else
                                   "OCR zakończony. Nie znaleziono tekstu do dodania. Plik pozostawiono bez zmian.")
            details = "Obrazy i wygląd stron zachowane."
            if self.ocr_result.get("fallback"):
                details += "\n"+self.ocr_result["fallback"]
            if self.ocr_result["backup"]:
                details += "\nKopia oryginału: "+self.ocr_result["backup"]
                self.backup_button.show()
            self.detail.setText(details)
            self.open_button.show()
            self.cancel_button.setText("Zamknij")
            self.cleanup()
        except Exception as error:
            self.failed(str(error))

    def failed(self,message):
        self.timer.stop()
        self.label.setText("Nie udało się wykonać OCR.")
        self.detail.setText(message+"\nPDF nie został podmieniony.")
        self.progress.hide()
        self.cancel_button.setText("Zamknij")
        self.cleanup()

    def process_error(self,error):
        if error==QProcess.FailedToStart:
            self.failed("Nie można uruchomić silnika OCR.")

    def open_backup(self):
        if self.ocr_result and self.ocr_result.get("backup"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.ocr_result["backup"]).parent)))

    def cleanup(self):
        if self.process.state()==QProcess.NotRunning and self.temporary:
            self.temporary.remove()
            self.temporary = None
        if self.process.state()==QProcess.NotRunning and self.job_temporary:
            self.job_temporary.remove()
            self.job_temporary = None

    def reject(self):
        self.cancelled = True
        if self.process.state()!=QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(3000)
        self.cleanup()
        super().reject()

    def closeEvent(self,event):
        self.reject()
        event.accept()
