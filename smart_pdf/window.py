from __future__ import annotations

import copy
import os
import sys
from datetime import datetime
from pathlib import Path

import pymupdf
from PySide6.QtCore import QItemSelectionModel, QProcess, QSettings, QSize, QStandardPaths, QTemporaryDir, QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QImage, QPixmap, QTextCharFormat, QTextCursor, QTransform, QUndoCommand, QUndoStack
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDockWidget, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QStackedWidget, QToolBar, QToolButton, QVBoxLayout, QWidget, QMenu, QFontComboBox, QAbstractSpinBox,
)

from smart_pdf import __version__
from smart_pdf.canvas import Canvas
from smart_pdf.dialogs import ScopeDialog
from smart_pdf.controls import DockTitle, PageDelegate, ValueSlider
from smart_pdf.export import export_pdf
from smart_pdf.model import Project, make_object, text_html, uid
from smart_pdf.ocr import available_languages, resources
from smart_pdf.style import STYLE


class EditCommand(QUndoCommand):
    def __init__(self,window,before,after,label):
        super().__init__(label)
        self.window,self.before,self.after = window,before,after
        self.initial = True

    def undo(self):
        self.window.restore_pages(self.before)

    def redo(self):
        if self.initial:
            self.initial = False
            self.window.revision += 1
            self.window.refresh_document()
        else:
            self.window.restore_pages(self.after)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        self.setWindowTitle("Smart PDF")
        self.resize(1440,940)
        self.settings = QSettings()
        self.project = None
        self.index = 0
        self.reading = False
        self.recovered = False
        self.refreshing = False
        self.live_before = None
        self.margin_side = "right"
        self.revision = 0
        self.autosaved_revision = -1
        self.recovery_id = uid()
        self.recovery_origin = None
        self.undo = QUndoStack(self)
        self.undo.setUndoLimit(100)
        self.undo.cleanChanged.connect(self.update_title)
        self.undo.indexChanged.connect(self.update_title)
        self.canvas = Canvas()
        self.canvas.committed.connect(self.commit)
        self.canvas.text_add_requested.connect(self.add_text)
        self.canvas.edit_text_requested.connect(self.edit_text)
        self.canvas.selection_changed.connect(self.sync_properties)
        self.canvas.file_dropped.connect(self.open_path)
        self.canvas.zoom_changed.connect(self.zoom_label)
        self.canvas.page_changed.connect(self.scrolled_page)
        self.canvas.text_editing_changed.connect(self.text_editing_changed)
        self.canvas.text_format_changed.connect(self.sync_text_format)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.welcome())
        self.stack.addWidget(self.canvas)
        self.setCentralWidget(self.stack)
        self.build_actions()
        self.build_toolbars()
        self.build_pages_panel()
        self.build_properties_panel()
        self.build_menus()
        self.ocr_process = QProcess(self)
        self.ocr_process.finished.connect(self.ocr_finished)
        self.ocr_process.errorOccurred.connect(self.ocr_error)
        self.ocr_queue = []
        self.ocr_current = None
        self.ocr_temp = None
        self.ocr_done = 0
        self.ocr_total = 0
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start(30000)
        self.thumbnail_timer = QTimer(self)
        self.thumbnail_timer.timeout.connect(self.render_next_thumbnail)
        self.thumbnail_queue = []
        self.thumb_cache = {}
        self.ocr_status = QLabel("OCR wyłączony • uruchom przyciskiem OCR")
        self.ocr_status.setMaximumWidth(285)
        self.ocr_status.setToolTip("OCR działa lokalnie i rozpoczyna się dopiero na Twoje polecenie.")
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addPermanentWidget(self.ocr_status)
        self.statusBar().showMessage("Otwórz PDF lub utwórz pusty dokument. Wszystkie operacje odbywają się lokalnie.")
        self.pages_dock.hide()
        self.properties_dock.hide()
        self.tools.hide()
        self.restoreGeometry(self.settings.value("geometry",b""))

    def action(self,label,callback,shortcut=None,checkable=False,canvas=False):
        parent = self.canvas if canvas else self
        action = QAction(label,parent)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(shortcut)
        if canvas:
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            self.canvas.addAction(action)
        action.triggered.connect(callback)
        return action

    def build_actions(self):
        self.new_action = self.action("Nowy",self.new_document,"Ctrl+N")
        self.open_action = self.action("Otwórz…",self.open_dialog,"Ctrl+O")
        self.save_action = self.action("Zapisz projekt",self.save_project,"Ctrl+S")
        self.save_as_action = self.action("Zapisz projekt jako…",lambda:self.save_project(True),"Ctrl+Shift+S")
        self.export_action = self.action("Eksportuj PDF…",self.export,"Ctrl+E")
        self.undo_action = self.undo.createUndoAction(self,"Cofnij")
        self.undo_action.setShortcut("Ctrl+Z")
        self.redo_action = self.undo.createRedoAction(self,"Ponów")
        self.redo_action.setShortcuts(["Ctrl+Y","Ctrl+Shift+Z"])
        self.copy_action = self.action("Kopiuj",lambda:self.canvas.copy(),"Ctrl+C",canvas=True)
        self.cut_action = self.action("Wytnij",lambda:self.canvas.copy(True),"Ctrl+X",canvas=True)
        self.paste_action = self.action("Wklej",self.canvas.paste,"Ctrl+V",canvas=True)
        self.delete_action = self.action("Usuń obiekty",self.canvas.delete_selected,"Delete",canvas=True)
        self.duplicate_action = self.action("Powiel obiekty",self.duplicate,"Ctrl+D",canvas=True)
        self.read_action = self.action("Tryb odczytu",self.toggle_reading,"Ctrl+Shift+R",True)
        self.fullscreen_action = self.action("Pełny ekran",self.toggle_fullscreen,"F11",True)
        self.fit_action = self.action("Dopasuj stronę",self.canvas.fit_page,"Ctrl+0")
        self.prev_page_action = self.action("Poprzednia strona",lambda:self.navigate_page(-1),"Ctrl+PgUp")
        self.next_page_action = self.action("Następna strona",lambda:self.navigate_page(1),"Ctrl+PgDown")
        self.rotate_action = self.action("Obróć strony…",self.rotate_pages)
        self.margin_action = self.action("Margines",lambda:self.add_margin("right"))
        self.ocr_action = self.action("OCR automatyczny",self.toggle_ocr,checkable=True)
        self.ocr_action.setChecked(False)
        self.ocr_now_action = self.action("OCR",lambda:self.start_ocr(True))
        self.ocr_repeat_action = self.action("Rozpoznaj ponownie wybrane skany",lambda:self.start_ocr(True,True))
        self.ocr_cancel_action = self.action("Anuluj OCR",self.cancel_ocr)
        self.settings_action = self.action("Ustawienia OCR…",self.ocr_settings)
        self.search_action = self.action("Szukaj tekstu",self.focus_search,"Ctrl+F")
        self.tool_group = QActionGroup(self)
        self.tool_actions = {}
        for kind,label,key in [("select_text","Zaznacz tekst","S"),("select","Obiekty","V"),
                               ("hand","Przesuwaj","G"),("pen","Pióro","P"),("text","Tekst","T"),
                               ("highlight","Zakreślacz","H"),("underline","Podkreślenie","U"),
                               ("strike","Przekreślenie",None),("line","Linia","L"),
                               ("ellipse","Okrąg",None),("triangle","Trójkąt",None),("rect","Prostokąt",None)]:
            action = self.action(label,lambda checked,k=kind:self.select_tool(k),key,True,True)
            self.tool_group.addAction(action)
            self.tool_actions[kind] = action
        self.tool_actions["select_text"].setChecked(True)

    def build_toolbars(self):
        self.header = QToolBar("Dokument",self)
        self.header.setMovable(False)
        self.header.setObjectName("document-toolbar")
        self.addToolBar(self.header)
        brand = QLabel("  SMART PDF  ")
        brand.setStyleSheet("font-size:15pt;font-weight:700;color:#245ade;padding-right:14px;")
        self.header.addWidget(brand)
        for action in (self.open_action,self.save_action,self.export_action):
            self.header.addAction(action)
        self.header.addSeparator()
        self.header.addAction(self.undo_action)
        self.header.addAction(self.redo_action)
        self.header.addSeparator()
        self.header.addAction(self.rotate_action)
        margin = QToolButton()
        margin.setDefaultAction(self.margin_action)
        margin.setPopupMode(QToolButton.MenuButtonPopup)
        menu = QMenu(margin)
        menu.addAction("Dodaj lewy margines",lambda:self.add_margin("left"))
        menu.addSeparator()
        menu.addAction("Prawy margines na zaznaczonych stronach",lambda:self.add_margin("right",self.selected_pages()))
        menu.addAction("Prawy margines na wszystkich stronach",lambda:self.add_margin("right",list(range(len(self.project.pages)))) if self.project else None)
        margin.setMenu(menu)
        margin.setToolTip("Kliknij: prawy margines z polem tekstowym. Strzałka: lewy margines i zakres.")
        self.header.addWidget(margin)
        self.header.addSeparator()
        self.header.addAction(self.read_action)
        self.header.addAction(self.ocr_now_action)
        self.addToolBarBreak()
        self.tools = QToolBar("Narzędzia edycji",self)
        self.tools.setObjectName("editing-toolbar")
        self.tools.setMovable(False)
        self.addToolBar(self.tools)
        for action in self.tool_actions.values():
            self.tools.addAction(action)
        self.tools.addSeparator()
        self.color_button = QPushButton("Kolor")
        self.color_button.clicked.connect(self.choose_color)
        self.tools.addWidget(self.color_button)
        self.update_color_button(self.canvas.color)
        self.tools.addWidget(QLabel(" Grubość "))
        self.stroke = ValueSlider(.3,30,2.5," pt")
        self.stroke.setFixedWidth(200)
        self.stroke.valueChanged.connect(self.stroke_changed)
        self.stroke.editingStarted.connect(self.begin_live_change)
        self.stroke.editingFinished.connect(self.end_live_change)
        self.tools.addWidget(self.stroke)
        self.zoom = QComboBox()
        self.zoom.addItems(["50%","75%","100%","125%","150%","200%","300%"])
        self.zoom.setCurrentText("100%")
        self.zoom.setToolTip("Podgląd jest renderowany do aktualnego powiększenia. Eksport zachowuje jakość oryginalnego PDF.")
        self.zoom.currentTextChanged.connect(lambda t:self.canvas.set_zoom(int(t.rstrip("%"))) if not self.refreshing else None)
        self.statusBar().addPermanentWidget(self.zoom)
        fit = QPushButton("Dopasuj")
        fit.clicked.connect(self.canvas.fit_page)
        self.statusBar().addPermanentWidget(fit)
        self.previous_button = QPushButton("‹")
        self.previous_button.setToolTip("Poprzednia strona • Ctrl+PageUp")
        self.previous_button.setMaximumWidth(32)
        self.previous_button.clicked.connect(lambda:self.navigate_page(-1))
        self.statusBar().addPermanentWidget(self.previous_button)
        self.page_number = QSpinBox()
        self.page_number.setMinimum(1)
        self.page_number.setMaximum(1)
        self.page_number.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.page_number.setAlignment(Qt.AlignCenter)
        self.page_number.setFixedWidth(42)
        self.page_number.valueChanged.connect(lambda n:self.page_list.setCurrentRow(n-1) if self.project and not self.refreshing else None)
        self.statusBar().addPermanentWidget(self.page_number)
        self.page_total = QLabel("/ 1")
        self.statusBar().addPermanentWidget(self.page_total)
        self.next_button = QPushButton("›")
        self.next_button.setToolTip("Następna strona • Ctrl+PageDown")
        self.next_button.setMaximumWidth(32)
        self.next_button.clicked.connect(lambda:self.navigate_page(1))
        self.statusBar().addPermanentWidget(self.next_button)

    def welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel("Smart PDF")
        title.setObjectName("hero")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Twój dokument. Twoje notatki. Wszystko lokalnie.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(26)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        open_button = QPushButton("Otwórz PDF lub projekt")
        open_button.setObjectName("primary")
        open_button.clicked.connect(self.open_dialog)
        row.addWidget(open_button)
        new_button = QPushButton("Pusty dokument")
        new_button.clicked.connect(self.new_document)
        row.addWidget(new_button)
        layout.addLayout(row)
        layout.addSpacing(20)
        hint = QLabel("Rysuj • zaznaczaj • pisz na dokumencie • dodawaj marginesy\n\n.smartpdf zachowuje obiekty     /     PDF do udostępnienia")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#78869b;line-height:150%;")
        layout.addWidget(hint)
        self.recovery_box = QVBoxLayout()
        layout.addLayout(self.recovery_box)
        QTimer.singleShot(0,self.show_recoveries)
        return page

    def build_pages_panel(self):
        self.pages_dock = QDockWidget("Strony",self)
        self.pages_dock.setObjectName("pages-dock")
        self.pages_dock.setMinimumWidth(195)
        self.pages_dock.setMaximumWidth(360)
        self.pages_dock.setTitleBarWidget(DockTitle(self.pages_dock,"Strony"))
        panel = QWidget()
        layout = QVBoxLayout(panel)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Szukaj w dokumencie…")
        self.search.returnPressed.connect(self.search_next)
        search_row.addWidget(self.search)
        next_button = QPushButton("→")
        next_button.setMaximumWidth(38)
        next_button.clicked.connect(self.search_next)
        search_row.addWidget(next_button)
        layout.addLayout(search_row)
        self.page_list = QListWidget()
        self.page_list.setItemDelegate(PageDelegate(self.page_list))
        self.page_list.setIconSize(QSize(125,150))
        self.page_list.setMouseTracking(True)
        self.page_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.page_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.page_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.page_list.currentRowChanged.connect(self.change_page)
        self.page_list.model().rowsMoved.connect(lambda *args:QTimer.singleShot(0,self.reorder_pages))
        self.page_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.page_list.customContextMenuRequested.connect(self.page_menu)
        layout.addWidget(self.page_list,1)
        self.page_label = QLabel("Ctrl + klik: wybierz wiele stron")
        self.page_label.setStyleSheet("font-size:9pt;color:#74839a;")
        layout.addWidget(self.page_label)
        self.pages_dock.setWidget(panel)
        self.addDockWidget(Qt.LeftDockWidgetArea,self.pages_dock)

    def build_properties_panel(self):
        self.properties_dock = QDockWidget("Właściwości obiektu",self)
        self.properties_dock.setObjectName("properties-dock")
        self.properties_dock.setMinimumWidth(235)
        self.properties_dock.setMaximumWidth(350)
        self.properties_dock.setTitleBarWidget(DockTitle(self.properties_dock,"Tekst i obiekty"))
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.property_hint = QLabel("Kliknij pole tekstowe i pisz na stronie.\nPrzesuwaj je za ramkę; uchwyty zmieniają rozmiar i obrót.")
        self.property_hint.setWordWrap(True)
        layout.addWidget(self.property_hint)
        self.swatches = QHBoxLayout()
        for color in ["#2864ed","#ef4d64","#ffcf40","#43bb8b","#9c67ed","#26334b"]:
            button = QPushButton()
            button.setFixedSize(26,26)
            button.setStyleSheet(f"background:{color};border:2px solid white;border-radius:13px;")
            button.setToolTip(color)
            button.clicked.connect(lambda checked,c=color:self.set_color(c))
            self.swatches.addWidget(button)
        layout.addLayout(self.swatches)
        self.text_controls = QWidget()
        text_form = QFormLayout(self.text_controls)
        text_form.setContentsMargins(0,8,0,8)
        self.fonts = QFontComboBox()
        self.fonts.setCurrentFont(QFont("Arial"))
        self.fonts.currentFontChanged.connect(lambda f:self.format_text(font=f.family()))
        text_form.addRow("Czcionka",self.fonts)
        self.font_size = QSpinBox()
        self.font_size.setRange(6,144)
        self.font_size.setValue(14)
        self.font_size.setSuffix(" pt")
        self.font_size.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.font_size.valueChanged.connect(lambda n:self.format_text(size=n))
        text_form.addRow("Rozmiar",self.font_size)
        row = QHBoxLayout()
        self.text_buttons = {}
        for key,label in [("bold","B"),("italic","I"),("underline","U")]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setFixedWidth(38)
            button.setToolTip({"bold":"Pogrubienie • Ctrl+B","italic":"Kursywa • Ctrl+I","underline":"Podkreślenie • Ctrl+U"}[key])
            button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(lambda checked,k=key:self.format_text(**{k:checked}))
            row.addWidget(button)
            self.text_buttons[key] = button
        self.text_align = QComboBox()
        self.text_align.addItems(["Do lewej","Środek","Do prawej"])
        self.text_align.currentIndexChanged.connect(lambda n:self.format_text(align=n))
        row.addWidget(self.text_align)
        text_form.addRow(row)
        layout.addWidget(self.text_controls)
        layout.addWidget(QLabel("Margines na bieżącej stronie"))
        self.margin_control = ValueSlider(15,160,55," mm")
        self.margin_control.valueChanged.connect(self.margin_width_changed)
        self.margin_control.editingStarted.connect(self.begin_live_change)
        self.margin_control.editingFinished.connect(self.end_live_change)
        layout.addWidget(self.margin_control)
        self.margin_hint = QLabel("Prawy • kliknij Margines, aby dodać")
        self.margin_hint.setStyleSheet("font-size:9pt;color:#74839a;")
        layout.addWidget(self.margin_hint)
        self.properties_form = QWidget()
        form = QFormLayout(self.properties_form)
        self.property_spins = {}
        for key,label in [("x","Pozycja X"),("y","Pozycja Y"),("w","Szerokość"),("h","Wysokość"),("rotation","Obrót"),("opacity","Krycie")]:
            spin = QDoubleSpinBox()
            spin.setDecimals(1 if key != "opacity" else 2)
            spin.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
            spin.setRange(-20000,20000)
            if key in {"w","h"}:
                spin.setRange(1,20000)
            if key == "width":
                spin.setRange(.2,100)
            if key == "opacity":
                spin.setRange(.02,1)
                spin.setSingleStep(.1)
            spin.setSuffix("°" if key == "rotation" else " pt" if key != "opacity" else "")
            spin.editingFinished.connect(lambda k=key,s=spin:self.set_property(k,s.value()))
            form.addRow(label,spin)
            self.property_spins[key] = spin
        fill_button = QPushButton("Wypełnienie kształtu…")
        fill_button.clicked.connect(self.choose_fill)
        form.addRow(fill_button)
        clear_fill = QPushButton("Usuń wypełnienie")
        clear_fill.clicked.connect(lambda:self.set_property("fill",""))
        form.addRow(clear_fill)
        self.edit_text_button = QPushButton("Pisz w wybranym polu")
        self.edit_text_button.clicked.connect(lambda:self.edit_text(self.canvas.selected_objects()[0]["id"]) if self.canvas.selected_objects() else None)
        form.addRow(self.edit_text_button)
        layout.addWidget(self.properties_form)
        layout.addStretch()
        hint = QLabel("Uchwyty na obiekcie:\n• prawy dolny: rozmiar\n• górny okrąg: obrót\n• Shift przy obrocie: co 15°")
        hint.setStyleSheet("color:#74839a;font-size:9pt;")
        layout.addWidget(hint)
        self.properties_dock.setWidget(panel)
        self.addDockWidget(Qt.RightDockWidgetArea,self.properties_dock)
        self.properties_form.setEnabled(False)

    def build_menus(self):
        file_menu = self.menuBar().addMenu("Plik")
        for action in (self.new_action,self.open_action,self.save_action,self.save_as_action,self.export_action):
            file_menu.addAction(action)
        file_menu.addSeparator()
        file_menu.addAction("Zamknij",self.close,"Alt+F4")
        edit = self.menuBar().addMenu("Edycja")
        for action in (self.undo_action,self.redo_action,self.copy_action,self.cut_action,self.paste_action,self.delete_action,self.duplicate_action):
            edit.addAction(action)
        pages = self.menuBar().addMenu("Strony")
        pages.addAction(self.rotate_action)
        pages.addAction(self.margin_action)
        pages.addAction("Dodaj lewy margines",lambda:self.add_margin("left"))
        pages.addAction("Usuń wybrane strony…",self.delete_pages)
        view = self.menuBar().addMenu("Widok")
        for action in (self.read_action,self.fullscreen_action,self.fit_action,self.search_action):
            view.addAction(action)
        view.addAction(self.prev_page_action)
        view.addAction(self.next_page_action)
        view.addSeparator()
        for widget in (self.header,self.tools,self.pages_dock,self.properties_dock):
            view.addAction(widget.toggleViewAction())
        ocr = self.menuBar().addMenu("OCR")
        for action in (self.ocr_action,self.ocr_now_action,self.ocr_repeat_action,self.ocr_cancel_action,self.settings_action):
            ocr.addAction(action)
        help_menu = self.menuBar().addMenu("Pomoc")
        self.update_action = self.action("Sprawdź aktualizacje…",self.check_updates)
        self.header.addSeparator()
        self.header.addAction(self.update_action)
        help_menu.addAction(self.update_action)
        help_menu.addAction("Skróty i zapis",self.help)
        help_menu.addAction("O programie",lambda:QMessageBox.about(self,"Smart PDF",f"Smart PDF {__version__}\nLokalny edytor PDF. Licencja AGPL-3.0-or-later.\nPySide6 / Qt, PyMuPDF / MuPDF, Tesseract."))

    def check_updates(self):
        from smart_pdf.updates import UpdateDialog
        dialog = UpdateDialog(self)
        dialog.exec()

    def selected_pages(self):
        return sorted(self.page_list.row(item) for item in self.page_list.selectedItems()) or [self.index]

    def mutate(self,label,callback):
        if not self.project or self.reading:
            return
        self.canvas.finish_text_edit()
        before = self.project.snapshot()
        active_id = self.project.pages[self.index].id
        callback()
        self.index = next((i for i,p in enumerate(self.project.pages) if p.id==active_id),min(self.index,len(self.project.pages)-1))
        self.commit(before,self.project.snapshot(),label)

    def commit(self,before,after,label):
        if before != after:
            ids = getattr(self.canvas,"next_selection",None) or [o["id"] for o in self.canvas.selected_objects()]
            self.canvas.next_selection = None
            self.undo.push(EditCommand(self,before,after,label))
            self.canvas.select_ids(ids)

    def restore_pages(self,pages):
        if not self.project:
            return
        current_id = self.project.pages[self.index].id if self.index < len(self.project.pages) else None
        self.project.restore(pages)
        self.index = next((i for i,p in enumerate(self.project.pages) if p.id==current_id),min(self.index,len(pages)-1))
        self.revision += 1
        self.refresh_document()

    def refresh_document(self,fit=False):
        if not self.project:
            return
        self.refreshing = True
        selected_ids = {item.data(Qt.UserRole) for item in self.page_list.selectedItems()}
        self.page_list.blockSignals(True)
        self.page_list.clear()
        self.thumbnail_queue = []
        for i,page in enumerate(self.project.pages):
            item = QListWidgetItem(f"Strona {i+1}" + (f" • {page.rotation}°" if page.rotation else ""))
            item.setData(Qt.UserRole,page.id)
            item.setTextAlignment(Qt.AlignCenter)
            item.setSizeHint(QSize(150,188))
            self.page_list.addItem(item)
            self.thumbnail_queue.append(i)
            item.setSelected(page.id in selected_ids)
        self.page_list.setCurrentRow(self.index,QItemSelectionModel.NoUpdate if selected_ids else QItemSelectionModel.ClearAndSelect)
        self.page_list.blockSignals(False)
        self.canvas.show_page(self.project,self.index,fit)
        self.thumbnail_timer.start(12)
        self.page_label.setText(f"{self.index+1} / {len(self.project.pages)}   •   Ctrl + klik: wiele stron")
        self.page_number.blockSignals(True)
        self.page_number.setMaximum(len(self.project.pages))
        self.page_total.setText(f"/ {len(self.project.pages)}")
        self.page_number.setValue(self.index+1)
        self.page_number.blockSignals(False)
        self.refreshing = False
        self.update_title()
        self.sync_properties()

    def render_next_thumbnail(self):
        if not self.thumbnail_queue or not self.project:
            self.thumbnail_timer.stop()
            return
        index = self.thumbnail_queue.pop(0)
        if index >= self.page_list.count():
            return
        state = self.project.pages[index]
        key = (state.source,state.rotation)
        if key not in self.thumb_cache:
            page = self.project.doc[state.source]
            scale = min(120/state.width,145/state.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            image = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format_RGB888).copy()
            qpix = QPixmap.fromImage(image).transformed(QTransform().rotate(state.rotation))
            self.thumb_cache[key] = QIcon(qpix)
        self.page_list.item(index).setIcon(self.thumb_cache[key])

    def change_page(self,index):
        if self.refreshing or not self.project or not 0 <= index < len(self.project.pages):
            return
        self.index = index
        self.canvas.scroll_to_page(index)
        self.page_label.setText(f"{index+1} / {len(self.project.pages)}   •   Ctrl + klik: wiele stron")
        self.page_number.blockSignals(True)
        self.page_number.setValue(index+1)
        self.page_number.blockSignals(False)
        self.canvas.setFocus()
        self.sync_margin()

    def scrolled_page(self,index):
        if self.refreshing or not self.project:
            return
        self.index = index
        self.page_list.blockSignals(True)
        self.page_list.setCurrentRow(index,QItemSelectionModel.NoUpdate)
        self.page_list.scrollToItem(self.page_list.item(index))
        self.page_list.blockSignals(False)
        self.page_number.blockSignals(True)
        self.page_number.setValue(index+1)
        self.page_number.blockSignals(False)
        self.page_label.setText(f"{index+1} / {len(self.project.pages)}   •   Ctrl + klik: wiele stron")
        self.sync_margin()

    def navigate_page(self,step):
        if self.project:
            index = min(len(self.project.pages)-1,max(0,self.index+step))
            self.page_list.setCurrentRow(index)

    def select_tool(self,kind):
        if self.reading and kind not in {"select_text","hand"}:
            return
        self.canvas.finish_text_edit()
        self.canvas.set_tool(kind)
        self.update_color_button(self.canvas.mark_color if kind in {"highlight","underline","strike"} else self.canvas.color)
        self.canvas.setFocus()

    def reorder_pages(self):
        if self.refreshing or not self.project or self.reading:
            return
        ids = [self.page_list.item(i).data(Qt.UserRole) for i in range(self.page_list.count())]
        if ids == [p.id for p in self.project.pages]:
            return
        by_id = {p.id:p for p in self.project.pages}
        self.mutate("Kolejność stron",lambda:setattr(self.project,"pages",[by_id[i] for i in ids]))

    def page_menu(self,position):
        from PySide6.QtWidgets import QMenu
        if not self.project or self.reading:
            return
        menu = QMenu(self)
        menu.addAction(self.rotate_action)
        menu.addAction(self.margin_action)
        menu.addAction("Usuń wybrane strony…",self.delete_pages)
        menu.exec(self.page_list.mapToGlobal(position))

    def open_dialog(self):
        path,_ = QFileDialog.getOpenFileName(self,"Otwórz dokument",self.settings.value("last_dir",""),"Dokumenty (*.pdf *.smartpdf)")
        if path:
            self.open_path(path)

    def open_path(self,path,recovery=False):
        if not self.maybe_save():
            return
        try:
            if str(path).lower().endswith(".smartpdf"):
                project = Project.load(path)
            else:
                try:
                    project = Project.from_pdf(path)
                except PermissionError:
                    password,ok = QInputDialog.getText(self,"Hasło PDF","Podaj hasło do PDF:",QLineEdit.Password)
                    if not ok:
                        return
                    project = Project.from_pdf(path,password)
            self.attach_project(project)
            if recovery:
                project.path = None
                project.dirty = True
                self.recovered = True
                self.recovery_origin = Path(path)
                self.revision += 1
                self.statusBar().showMessage("Odzyskano projekt. Zapisz go jako nowy plik .smartpdf.",10000)
            if not recovery:
                self.settings.setValue("last_dir",str(Path(path).parent))
            self.update_title()
        except Exception as error:
            self.error("Nie można otworzyć dokumentu",error)

    def attach_project(self,project):
        self.cancel_ocr()
        if self.project:
            self.remove_recovery()
            self.project.doc.close()
        self.project,self.index = project,0
        self.recovered = False
        self.undo.clear()
        self.undo.setClean()
        self.revision,self.autosaved_revision = 0,-1
        self.recovery_id = uid()
        self.recovery_origin = None
        self.thumb_cache.clear()
        self.stack.setCurrentWidget(self.canvas)
        self.canvas.reading = self.reading
        self.tools.setVisible(not self.reading)
        self.pages_dock.setVisible(not self.reading)
        self.properties_dock.setVisible(not self.reading)
        self.refresh_document(True)
        self.canvas.setFocus()
        self.statusBar().showMessage("Przewijaj dokument w dół. Kliknij pole tekstowe, aby pisać bezpośrednio na stronie.",8000)
        QTimer.singleShot(200,self.start_ocr)

    def new_document(self):
        if self.maybe_save():
            self.attach_project(Project.blank())

    def save_project(self,save_as=False):
        if not self.project:
            return False
        self.canvas.finish_text_edit()
        path = self.project.path if not save_as else None
        if not path:
            path,_ = QFileDialog.getSaveFileName(self,"Zapisz edytowalny projekt",str(Path(self.settings.value("last_dir",""))/f"{self.project.title}.smartpdf"),"Projekt Smart PDF (*.smartpdf)")
            if not path:
                return False
            if not str(path).lower().endswith(".smartpdf"):
                path += ".smartpdf"
        try:
            self.project.save(path)
            self.recovered = False
            self.undo.setClean()
            self.remove_recovery()
            self.autosaved_revision = self.revision
            self.update_title()
            self.statusBar().showMessage("Projekt zapisany — obiekty pozostają edytowalne.",6000)
            return True
        except Exception as error:
            self.error("Nie można zapisać projektu",error)
            return False

    def export(self):
        if not self.project:
            return
        self.canvas.finish_text_edit()
        path,_ = QFileDialog.getSaveFileName(self,"Eksportuj zwykły PDF",str(Path(self.settings.value("last_dir",""))/f"{self.project.title}-edycja.pdf"),"PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            export_pdf(self.project,path)
            self.statusBar().showMessage("PDF wyeksportowany. Zapisz też .smartpdf, aby zachować edytowalne obiekty.",10000)
        except Exception as error:
            self.error("Nie można wyeksportować PDF",error)

    def maybe_save(self):
        self.canvas.finish_text_edit()
        self.end_live_change()
        if not self.project or (self.undo.isClean() and not self.project.dirty):
            return True
        reply = QMessageBox.question(self,"Niezapisany projekt","Zapisać zmiany w edytowalnym projekcie .smartpdf?",QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Save)
        if reply == QMessageBox.Save:
            return self.save_project()
        if reply == QMessageBox.Discard:
            self.remove_recovery()
            return True
        return False

    def update_title(self,*args):
        dirty = self.project and (not self.undo.isClean() or self.recovered)
        if self.project:
            self.project.dirty = bool(dirty)
        name = self.project.title if self.project else ""
        self.setWindowTitle(f"{'● ' if dirty else ''}{name + ' — ' if name else ''}Smart PDF")

    def add_text(self,x,y):
        if not self.project or self.reading:
            return
        obj = make_object("text",x,y,240,60,html=text_html("",self.font_size.value(),self.canvas.color))
        self.mutate("Dodanie tekstu",lambda:self.project.pages[self.index].objects.append(obj))
        self.tool_actions["select_text"].setChecked(True)
        self.canvas.set_tool("select_text")
        self.canvas.start_text_edit(obj["id"])

    def edit_text(self,identifier):
        if not self.project or self.reading:
            return
        self.canvas.start_text_edit(identifier)

    def duplicate(self):
        self.canvas.copy()
        self.canvas.paste()

    def rotate_pages(self):
        if not self.project or self.reading:
            return
        dialog = ScopeDialog("Obróć strony PDF",self.index,self.selected_pages(),len(self.project.pages),parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        angle = [90,-90,180][dialog.angle.currentIndex()]
        def change():
            for index in dialog.indices():
                page = self.project.pages[index]
                page.rotation = (page.rotation+angle)%360
        self.mutate("Obrót stron",change)
        self.canvas.fit_page()

    def local_margin_side(self,index,side=None):
        ring = ["top","right","bottom","left"]
        return ring[(ring.index(side or self.margin_side)-self.project.pages[index].rotation//90)%4]

    def add_margin(self,side="right",indices=None):
        if not self.project or self.reading:
            return
        self.canvas.finish_text_edit()
        self.margin_side = side
        targets = indices if indices is not None else [self.index]
        width = self.margin_control.value()*72/25.4
        def change():
            for index in targets:
                local = self.local_margin_side(index,side)
                points = self.project.pages[index].margins[local] or width
                self.project.add_margin([index],local,points)
        self.mutate("Margines z polem na notatki",change)
        self.properties_dock.show()
        self.sync_margin()
        local = self.local_margin_side(self.index,side)
        notes = next((o for o in self.project.pages[self.index].objects if o.get("margin_side")==local),None)
        if notes:
            self.tool_actions["select_text"].setChecked(True)
            self.canvas.set_tool("select_text")
            item = self.canvas.items_by_id[notes["id"]]
            self.canvas.ensureVisible(item,40,30)
            self.canvas.start_text_edit(notes["id"])

    def sync_margin(self):
        if not self.project or not hasattr(self,"margin_control"):
            return
        points = self.project.pages[self.index].margins[self.local_margin_side(self.index)]
        if points:
            self.margin_control.setValue(points*25.4/72)
        self.margin_hint.setText(("Prawy" if self.margin_side=="right" else "Lewy") + (" • przeciągnij suwak" if points else " • kliknij Margines, aby dodać"))

    def begin_live_change(self):
        self.end_live_change()
        self.canvas.finish_text_edit()
        if self.project and not self.reading:
            self.live_before = self.project.snapshot()

    def end_live_change(self):
        if self.live_before is not None:
            before,self.live_before = self.live_before,None
            self.commit(before,self.project.snapshot(),"Zmiana suwakiem")

    def live_change(self,callback):
        if not self.project or self.reading:
            return
        if self.live_before is None:
            self.mutate("Zmiana wartości",callback)
        else:
            callback()
            self.project.dirty = True
            self.canvas.show_page(self.project,self.index)

    def stroke_changed(self,value):
        self.canvas.stroke_width = value
        if self.refreshing:
            return
        selected = [o for o in self.canvas.selected_objects() if o["kind"] not in {"text","replacement"}]
        if selected:
            self.live_change(lambda:[o.update(width=value) for o in selected])

    def margin_width_changed(self,value):
        if not self.project or self.refreshing:
            return
        local = self.local_margin_side(self.index)
        if self.project.pages[self.index].margins[local]:
            self.live_change(lambda:self.project.add_margin([self.index],local,value*72/25.4))

    def delete_pages(self):
        if not self.project or self.reading:
            return
        indices = self.selected_pages()
        if len(indices)>=len(self.project.pages):
            self.statusBar().showMessage("Dokument musi zachować przynajmniej jedną stronę.",5000)
            return
        if QMessageBox.question(self,"Usuń strony",f"Usunąć {len(indices)} stron? Można cofnąć tę zmianę.") == QMessageBox.Yes:
            self.mutate("Usunięcie stron",lambda:setattr(self.project,"pages",[p for i,p in enumerate(self.project.pages) if i not in indices]))

    def set_color(self,color):
        self.canvas.color = self.canvas.mark_color = color
        self.update_color_button(color)
        if self.canvas.editing:
            self.format_text(color=color)
            return
        selected = self.canvas.selected_objects()
        if selected:
            def change():
                for obj in selected:
                    obj["color"] = color
                    if obj["kind"] in {"text","replacement"}:
                        from smart_pdf.painting import rich_document
                        from PySide6.QtGui import QTextCharFormat,QTextCursor
                        doc = rich_document(obj)
                        cursor = QTextCursor(doc)
                        cursor.select(QTextCursor.Document)
                        fmt = QTextCharFormat()
                        fmt.setForeground(QColor(color))
                        cursor.mergeCharFormat(fmt)
                        obj["html"] = doc.toHtml()
            self.mutate("Kolor obiektów",change)

    def choose_color(self):
        active_color = self.canvas.mark_color if self.canvas.tool in {"highlight","underline","strike"} else self.canvas.color
        color = QColorDialog.getColor(QColor(active_color),self,"Kolor rysowania / zaznaczenia")
        if color.isValid():
            self.set_color(color.name())

    def update_color_button(self,color):
        self.color_button.setStyleSheet(f"border-bottom:4px solid {color};padding:5px 10px;background:white;")

    def choose_fill(self):
        color = QColorDialog.getColor(QColor(self.canvas.fill or "#e0ebff"),self,"Wypełnienie")
        if color.isValid():
            self.canvas.fill = color.name()
            self.set_property("fill",color.name())

    def set_property(self,key,value):
        if self.refreshing or not self.project or self.reading:
            return
        selected = self.canvas.selected_objects()
        if not selected:
            return
        if all(o.get(key)==value for o in selected):
            return
        self.mutate("Właściwości obiektu",lambda:[o.update({key:value}) for o in selected])

    def sync_properties(self):
        if self.refreshing:
            return
        selected = self.canvas.selected_objects()
        text_selected = len(selected)==1 and selected[0]["kind"] in {"text","replacement"}
        self.text_controls.setEnabled(text_selected and not self.reading)
        self.properties_form.setEnabled(bool(selected) and not self.reading)
        if selected:
            self.refreshing = True
            obj = selected[0]
            if obj.get("margin_side"):
                item = self.canvas.items_by_id[obj["id"]]
                ring = ["top","right","bottom","left"]
                displayed_side = ring[(ring.index(obj["margin_side"])+self.project.pages[item.page_index].rotation//90)%4]
                if item.page_index==self.index and displayed_side in {"left","right"}:
                    self.margin_side = displayed_side
            self.property_hint.setText(f"Wybrano obiekty: {len(selected)}\nWartości dotyczą pierwszego obiektu.")
            for key,spin in self.property_spins.items():
                spin.setValue(obj.get(key,0))
            if obj["kind"] not in {"text","replacement"}:
                self.stroke.setValue(obj["width"])
            self.edit_text_button.setEnabled(len(selected)==1 and obj["kind"] in {"text","replacement"})
            self.refreshing = False
        else:
            self.property_hint.setText("Kliknij pole tekstowe i pisz na stronie.\nPrzesuwaj je za ramkę; uchwyty zmieniają rozmiar i obrót.")
        self.sync_margin()

    def text_editing_changed(self,editing):
        actions = [*self.tool_actions.values(),self.copy_action,self.cut_action,self.paste_action,self.delete_action,self.duplicate_action,self.undo_action,self.redo_action]
        for action in actions:
            if editing:
                action._text_shortcuts = action.shortcuts()
                action.setShortcuts([])
            elif hasattr(action,"_text_shortcuts"):
                action.setShortcuts(action._text_shortcuts)
        if hasattr(self,"text_controls"):
            self.text_controls.setEnabled(editing)

    def sync_text_format(self):
        if not self.canvas.editing or not hasattr(self,"fonts"):
            return
        editor = self.canvas.editing.editor
        fmt = editor.textCursor().charFormat()
        widgets = [self.fonts,self.font_size,self.text_align,*self.text_buttons.values()]
        for widget in widgets:
            widget.blockSignals(True)
        self.fonts.setCurrentFont(fmt.font())
        self.font_size.setValue(round(fmt.fontPointSize() or 14))
        self.text_buttons["bold"].setChecked(fmt.fontWeight()>=QFont.Bold)
        self.text_buttons["italic"].setChecked(fmt.fontItalic())
        self.text_buttons["underline"].setChecked(fmt.fontUnderline())
        alignment = editor.textCursor().blockFormat().alignment()
        self.text_align.setCurrentIndex(1 if alignment & Qt.AlignHCenter else 2 if alignment & Qt.AlignRight else 0)
        for widget in widgets:
            widget.blockSignals(False)

    def format_text(self,**options):
        if self.refreshing or self.reading or not self.project:
            return
        if not self.canvas.editing:
            selected = self.canvas.selected_objects()
            if len(selected)!=1 or selected[0]["kind"] not in {"text","replacement"}:
                return
            self.canvas.start_text_edit(selected[0]["id"])
        editor = self.canvas.editing.editor
        cursor = editor.textCursor()
        fmt = QTextCharFormat()
        if "font" in options: fmt.setFontFamilies([options["font"]])
        if "size" in options: fmt.setFontPointSize(options["size"])
        if "bold" in options: fmt.setFontWeight(QFont.Bold if options["bold"] else QFont.Normal)
        if "italic" in options: fmt.setFontItalic(options["italic"])
        if "underline" in options: fmt.setFontUnderline(options["underline"])
        if "color" in options: fmt.setForeground(QColor(options["color"]))
        if "align" in options:
            block = cursor.blockFormat()
            block.setAlignment([Qt.AlignLeft,Qt.AlignHCenter,Qt.AlignRight][options["align"]])
            cursor.mergeBlockFormat(block)
        else:
            cursor.mergeCharFormat(fmt)
        editor.setTextCursor(cursor)
        editor.setFocus()
        self.sync_text_format()

    def toggle_reading(self,checked):
        self.canvas.finish_text_edit()
        self.reading = bool(checked)
        self.canvas.reading = self.reading
        self.tools.setVisible(bool(self.project) and not checked)
        self.properties_dock.setVisible(bool(self.project) and not checked)
        self.pages_dock.setVisible(bool(self.project) and not checked)
        self.page_list.setDragDropMode(QAbstractItemView.NoDragDrop if checked else QAbstractItemView.InternalMove)
        self.canvas.scene().clearSelection()
        kind = "select_text"
        self.tool_actions[kind].setChecked(True)
        self.canvas.set_tool(kind)
        for action in (self.undo_action,self.redo_action,self.rotate_action,self.margin_action):
            action.setEnabled(not checked and (self.undo.canUndo() if action==self.undo_action else self.undo.canRedo() if action==self.redo_action else True))
        self.canvas.setFocus()
        self.statusBar().showMessage("Tryb odczytu • Ctrl+Shift+R wraca do edycji" if checked else "Tryb edycji",5000)

    def toggle_fullscreen(self,checked):
        self.showFullScreen() if checked else self.showNormal()

    def zoom_label(self,percent):
        self.zoom.blockSignals(True)
        text = f"{percent}%"
        if self.zoom.findText(text)<0:
            self.zoom.addItem(text)
        self.zoom.setCurrentText(text)
        self.zoom.blockSignals(False)

    def focus_search(self):
        if self.project:
            self.pages_dock.show()
            self.search.setFocus()
            self.search.selectAll()

    def search_next(self):
        query = self.search.text().strip().casefold()
        if not self.project or not query:
            return
        signature = (query,self.revision,len(self.project.ocr))
        if getattr(self,"search_signature",None) != signature:
            self.search_results = []
            for index in range(len(self.project.pages)):
                words = self.project.words(index)
                # Match whole phrases while retaining word positions.
                combined = ""
                spans = []
                for word in words:
                    start = len(combined)
                    combined += word[4].casefold()+" "
                    spans.append((start,len(combined)-1,word))
                offset = 0
                while (position:=combined.find(query,offset))>=0:
                    hit = [word for a,b,word in spans if a < position+len(query) and b>position]
                    if hit:
                        self.search_results.append((index,hit))
                    offset = position+max(1,len(query))
            self.search_cursor = -1
            self.search_signature = signature
        if not self.search_results:
            self.statusBar().showMessage("Brak wyników. Skany będą przeszukiwalne po ukończeniu OCR.",5000)
            return
        self.search_cursor = (self.search_cursor+1)%len(self.search_results)
        index,words = self.search_results[self.search_cursor]
        self.page_list.setCurrentRow(index)
        self.canvas.clear_text_selection()
        self.canvas.selected_words = words
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPen
        from PySide6.QtWidgets import QGraphicsRectItem
        for a,b,c,d in self.canvas.selection_rects(words):
            item = QGraphicsRectItem(QRectF(a,b,c-a,d-b),self.canvas.root)
            item.setPen(QPen(Qt.NoPen))
            item.setBrush(QColor(255,197,40,110))
            item.setZValue(50)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self.canvas.selection_items.append(item)
        self.canvas.centerOn(self.canvas.root.mapToScene((words[0][0]+words[0][2])/2,(words[0][1]+words[0][3])/2))
        self.statusBar().showMessage(f"Wynik {self.search_cursor+1} / {len(self.search_results)} — strona {index+1}",5000)

    def toggle_ocr(self,checked):
        self.settings.setValue("auto_ocr",checked)
        if checked:
            self.start_ocr()
        else:
            self.cancel_ocr()
            self.ocr_status.setText("OCR automatyczny wyłączony")

    def start_ocr(self,manual=False,repeat=False):
        if not self.project or (not manual and not self.ocr_action.isChecked()) or self.ocr_process.state()!=QProcess.NotRunning:
            return
        languages = self.settings.value("ocr_languages","pol+eng")
        missing = set(languages.split("+"))-set(available_languages())
        if missing:
            self.ocr_status.setText("Brak modeli OCR")
            if manual:
                QMessageBox.information(self,"Modele OCR","Brak modeli: "+", ".join(sorted(missing))+".\nUruchom scripts/fetch_ocr.py lub zainstaluj pełną wersję Smart PDF.")
            return
        candidates = [self.project.pages[i] for i in self.selected_pages()] if repeat else self.project.pages
        self.ocr_queue = sorted({p.source for p in candidates if self.project.needs_ocr(p.source) or
                                 (repeat and len(self.project.doc[p.source].get_text().strip())<20)})
        self.ocr_total,self.ocr_done = len(self.ocr_queue),0
        if not self.ocr_queue:
            self.ocr_status.setText("Warstwa tekstu dostępna")
            return
        self.ocr_temp = QTemporaryDir()
        Path(self.ocr_temp.path(),"source.pdf").write_bytes(self.project.source_pdf)
        self.ocr_next()

    def ocr_next(self):
        if not self.ocr_queue or not self.project:
            self.ocr_status.setText(f"OCR ukończony ({self.ocr_done} stron)")
            self.ocr_current = None
            return
        source = self.ocr_queue.pop(0)
        output = str(Path(self.ocr_temp.path(),f"ocr-{source}.pdf"))
        self.ocr_current = (source,output)
        languages = self.settings.value("ocr_languages","pol+eng")
        orientation = self.project.pages[self.index].rotation if self.project.pages[self.index].source==source else next(p.rotation for p in self.project.pages if p.source==source)
        args = ["--ocr-worker",str(Path(self.ocr_temp.path(),"source.pdf")),output,str(source),languages,str(self.settings.value("ocr_dpi",300,type=int)),str(orientation)]
        if not getattr(sys,"frozen",False):
            args = ["-m","smart_pdf",*args]
        self.ocr_status.setText(f"OCR lokalny • {self.ocr_done+1} / {self.ocr_total}")
        self.ocr_process.setProgram(sys.executable)
        self.ocr_process.setArguments(args)
        self.ocr_process.start()

    def ocr_finished(self,code,status):
        current,self.ocr_current = self.ocr_current,None
        if not current or not self.project:
            return
        source,output = current
        if code!=0 or not Path(output).exists():
            detail_path = Path(output+".error")
            detail = detail_path.read_text(encoding="utf-8") if detail_path.exists() else bytes(self.ocr_process.readAllStandardError()).decode(errors="replace")
            self.ocr_queue.clear()
            self.ocr_status.setText("OCR: błąd — można ponowić")
            self.statusBar().showMessage("OCR nie powiódł się: "+detail[:300],15000)
            return
        self.project.ocr[source] = Path(output).read_bytes()
        self.project.ocr_languages[source] = self.settings.value("ocr_languages","pol+eng")
        self.project.cache_dirty = True
        self.revision += 1
        self.ocr_done += 1
        if self.project.pages[self.index].source == source:
            self.canvas.words = self.project.words(self.index)
        QTimer.singleShot(20,self.ocr_next)

    def ocr_error(self,error):
        if error == QProcess.FailedToStart:
            self.ocr_queue.clear()
            self.ocr_current = None
            self.ocr_status.setText("Nie można uruchomić OCR")

    def cancel_ocr(self):
        if not hasattr(self,"ocr_process"):
            return
        self.ocr_queue.clear()
        self.ocr_current = None
        if self.ocr_process.state()!=QProcess.NotRunning:
            self.ocr_process.kill()
            self.ocr_process.waitForFinished(3000)
        self.ocr_temp = None
        self.ocr_status.setText("OCR wyłączony")

    def ocr_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ustawienia lokalnego OCR")
        form = QFormLayout(dialog)
        languages = QComboBox()
        languages.addItems(["Polski + angielski","Polski","Angielski"])
        codes = ["pol+eng","pol","eng"]
        current = self.settings.value("ocr_languages","pol+eng")
        languages.setCurrentIndex(codes.index(current) if current in codes else 0)
        form.addRow("Języki",languages)
        quality = QComboBox()
        quality.addItems(["200 DPI — szybciej","300 DPI — domyślnie","400 DPI — drobny tekst"])
        quality.setCurrentIndex([200,300,400].index(self.settings.value("ocr_dpi",300,type=int)))
        form.addRow("Jakość",quality)
        form.addRow(QLabel("Tesseract LSTM / tessdata_best\nOCR używa lokalnego CPU (do 2 wątków), bez połączenia z internetem.\nAutomatycznie rozpoznaje strony bez użytecznej warstwy tekstu.\nZmiana języka dotyczy kolejnych rozpoznawanych stron."))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec()==QDialog.Accepted:
            self.cancel_ocr()
            self.settings.setValue("ocr_languages",codes[languages.currentIndex()])
            self.settings.setValue("ocr_dpi",[200,300,400][quality.currentIndex()])
            self.start_ocr()

    def recovery_dir(self):
        path = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))/"recovery"
        path.mkdir(parents=True,exist_ok=True)
        return path

    def recovery_path(self):
        return self.recovery_dir()/f"{self.recovery_id}.smartpdf"

    def autosave(self):
        if self.project and self.revision != self.autosaved_revision and (self.project.dirty or self.project.cache_dirty or not self.undo.isClean()):
            try:
                self.project.save(self.recovery_path(),autosave=True)
                self.autosaved_revision = self.revision
            except Exception as error:
                self.statusBar().showMessage(f"Nie udało się zapisać kopii odzyskiwania: {error}",10000)

    def remove_recovery(self):
        self.recovery_path().unlink(missing_ok=True)
        if self.recovery_origin:
            self.recovery_origin.unlink(missing_ok=True)
            self.recovery_origin = None

    def show_recoveries(self):
        files = sorted(self.recovery_dir().glob("*.smartpdf"),key=lambda p:p.stat().st_mtime,reverse=True)[:5]
        if files:
            label = QLabel("Dostępne kopie po przerwaniu pracy:")
            label.setAlignment(Qt.AlignCenter)
            self.recovery_box.addWidget(label)
        for path in files:
            title = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
            button = QPushButton(f"Odzyskaj projekt • {title}")
            button.clicked.connect(lambda checked,p=path:self.open_path(p,True))
            self.recovery_box.addWidget(button)

    def help(self):
        QMessageBox.information(self,"Skróty i zapis",
            "Ctrl+O: otwórz • Ctrl+S: zapisz projekt • Ctrl+E: eksport PDF\n"
            "Ctrl+Z: cofnij • Ctrl+Y: ponów\n"
            "Ctrl+C / X / V: kopiuj / wytnij / wklej obiekty\n"
            "Delete: usuń • Ctrl+D: powiel obiekty\n"
            "V: obiekty • S: zaznacz tekst • P: pióro • T: tekst\n"
            "H: zakreślacz • U: podkreślenie • L: linia • G: przesuwanie\n"
            "Ctrl+F: wyszukiwanie • Ctrl+kółko: zoom • Ctrl+0: dopasuj\n"
            "Ctrl+Shift+R: odczyt • F11: pełny ekran\n\n"
            "Skróty obiektów i narzędzi działają przy aktywnym dokumencie.\n"
            "Projekt .smartpdf zawiera oryginał, obiekty i OCR.\n"
            "Eksport PDF zachowuje wygląd i warstwę tekstu. Obiekty stają się treścią strony.\n"
            "Kopia odzyskiwania jest zapisywana co 30 sekund.")

    def error(self,title,error):
        QMessageBox.critical(self,title,str(error))

    def closeEvent(self,event):
        if not self.maybe_save():
            event.ignore()
            return
        self.cancel_ocr()
        self.autosave_timer.stop()
        self.thumbnail_timer.stop()
        self.thumbnail_queue.clear()
        self.settings.setValue("geometry",self.saveGeometry())
        if self.project:
            self.remove_recovery()
            self.project.doc.close()
        self.project = None
        self.canvas.show_page(None,0)
        self.thumb_cache.clear()
        event.accept()
